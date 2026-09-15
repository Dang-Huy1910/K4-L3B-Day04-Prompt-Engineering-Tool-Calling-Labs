from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from action_guard import guard_ticket_call, latest_user_text
from providers.base import Provider, ToolCall
from tools import TOOL_FUNCTIONS


@dataclass
class AgentRun:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class HelpdeskAgent:
    def __init__(
        self,
        provider: Provider,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model = model

    def run(self, user_messages: list[dict[str, str]], *, tool_choice: Any | None = None) -> AgentRun:
        messages = [{"role": "system", "content": self.system_prompt}, *user_messages]
        response = self.provider.complete(
            messages,
            self.tools,
            model=self.model,
            temperature=0.0,
            tool_choice=tool_choice,
        )
        results: list[dict[str, Any]] = []
        current_user_text = latest_user_text(user_messages)
        for call in response.tool_calls:
            func = TOOL_FUNCTIONS.get(call.name)
            if not func:
                results.append({"tool": call.name, "error": "unknown_tool"})
                continue
            if call.name == "create_ticket":
                allowed, reason = guard_ticket_call(
                    call.args,
                    current_user_text,
                    conversation_text="\n".join(
                        message.get("content", "")
                        for message in user_messages
                        if message.get("role") == "user"
                    ),
                )
                if not allowed:
                    results.append({
                        "tool": call.name,
                        "args": call.args,
                        "result": {
                            "tool": call.name,
                            "error": "action_blocked",
                            "reason": reason,
                            "message": "A current explicit confirmation for this exact ticket payload is required.",
                        },
                    })
                    continue
            try:
                result = func(**call.args)
            except Exception as exc:  # keep eval robust; failures are evidence
                result = {"error": type(exc).__name__, "message": str(exc)}
            results.append({"tool": call.name, "args": call.args, "result": result})
        return AgentRun(text=response.text, tool_calls=response.tool_calls, tool_results=results)
