from __future__ import annotations

import json
import os
import time
from typing import Any

from providers.base import ModelResponse, ToolCall


def _is_retryable_provider_error(exc: Exception) -> bool:
    message = str(exc)
    lowered = message.casefold()
    if "perday" in lowered or "requests per day" in lowered:
        return False
    return any(
        marker in message
        for marker in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "500", "InternalServerError")
    )


def _to_gemini_declarations(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    for item in tools or []:
        function = item.get("function", item)
        declarations.append({
            "name": function["name"],
            "description": function.get("description", ""),
            "parameters": function.get("parameters", {"type": "object", "properties": {}}),
        })
    return declarations


def _to_gemini_contents(messages: list[dict[str, str]]) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
    return ("\n\n".join(system_parts) if system_parts else None), contents


def _part_text(part: Any) -> str | None:
    if hasattr(part, "text"):
        return getattr(part, "text")
    if isinstance(part, dict):
        return part.get("text")
    return None


def _part_function_call(part: Any) -> Any | None:
    if hasattr(part, "function_call"):
        return getattr(part, "function_call")
    if isinstance(part, dict):
        return part.get("function_call")
    return None


def _function_call_name(call: Any) -> str | None:
    if hasattr(call, "name"):
        return getattr(call, "name")
    if isinstance(call, dict):
        return call.get("name")
    return None


def _function_call_args(call: Any) -> dict[str, Any]:
    if hasattr(call, "args"):
        return dict(getattr(call, "args") or {})
    if isinstance(call, dict):
        return dict(call.get("args") or {})
    return {}


class GeminiProvider:
    """Google Gemini API provider with normalized tool_calls output."""

    def __init__(
        self,
        *,
        api_key_env: str = "GEMINI_API_KEY",
        default_model: str = "gemini-3.6-flash",
    ) -> None:
        self.api_key_env = api_key_env
        self.default_model = default_model

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
    ) -> ModelResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("Install live provider dependency first: pip install google-genai") from exc

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.api_key_env}")

        system_instruction, contents = _to_gemini_contents(messages)
        declarations = _to_gemini_declarations(tools)
        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if declarations:
            config_kwargs["tools"] = [types.Tool(function_declarations=declarations)]
            if tool_choice == "required":
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.ANY
                    )
                )
            elif tool_choice == "none":
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.NONE
                    )
                )
            elif tool_choice == "auto":
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO
                    )
                )
            elif isinstance(tool_choice, dict) and "function" in tool_choice:
                func_name = tool_choice["function"].get("name")
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.ANY,
                        allowed_function_names=[func_name] if func_name else None,
                    )
                )

        client = genai.Client(api_key=api_key)
        target_model = model or self.default_model
        gen_config = types.GenerateContentConfig(**config_kwargs)

        last_exc: Exception | None = None
        resp = None
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=gen_config,
                )
                break
            except Exception as exc:
                last_exc = exc
                if _is_retryable_provider_error(exc):
                    time.sleep(2 ** attempt + 1)
                    continue
                raise
        if resp is None and last_exc:
            raise last_exc

        text_parts: list[str] = []
        calls: list[ToolCall] = []

        def append_call(function_call: Any) -> None:
            name = _function_call_name(function_call)
            if name:
                calls.append(ToolCall(name=name, args=_function_call_args(function_call)))

        for candidate in getattr(resp, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                text = _part_text(part)
                if text:
                    text_parts.append(text)
                function_call = _part_function_call(part)
                if function_call:
                    append_call(function_call)

        # Some SDK versions expose function calls directly on the response.
        for function_call in getattr(resp, "function_calls", []) or []:
            append_call(function_call)

        deduped_calls: list[ToolCall] = []
        seen: set[tuple[str, str]] = set()
        for call in calls:
            key = (call.name, json.dumps(call.args, ensure_ascii=False, sort_keys=True))
            if key not in seen:
                seen.add(key)
                deduped_calls.append(call)

        return ModelResponse(text="\n".join(part for part in text_parts if part) or None, tool_calls=deduped_calls, raw=resp)
