from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from providers.base import Provider, ToolCall
from tools import TOOL_FUNCTIONS
from versioning import ArtifactVersion, artifact_version_dict, build_artifact_version


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No local implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for an incident report and the findings are ready, "
            "call the reporting tool. Otherwise answer directly, state uncertainty, and give the safest next step."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


CANCEL_PATTERNS = re.compile(
    r"\b(?:hủy|huy|thôi|dung lai|dừng lại|cancel|stop|nevermind|forget it)\b",
    re.IGNORECASE,
)


@dataclass
class ConversationSession:
    session_id: str
    version: str
    system_prompt_path: Path
    tools_path: Path
    provider_name: str
    model: str | None = None
    history_window: int = 5
    max_tool_rounds: int = 4
    turns: list[dict[str, Any]] = field(default_factory=list)
    pending_clarification: dict[str, Any] | None = None
    pending_action: dict[str, Any] | None = None
    created_at: str = field(default_factory=now_iso)

    def get_artifact_version(self) -> ArtifactVersion:
        return build_artifact_version(self.version, self.system_prompt_path, self.tools_path)

    def reset(self) -> None:
        self.turns.clear()
        self.pending_clarification = None
        self.pending_action = None

    def build_messages(self, user_text: str, system_prompt: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        recent_turns = self.turns[-self.history_window:] if self.history_window > 0 else []

        for turn in recent_turns:
            user_msg = turn.get("user")
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            # Include tool context if present in turn rounds
            for round_record in turn.get("rounds", []):
                tool_calls = [
                    ToolCall(name=c["name"], args=c["args"])
                    for c in round_record.get("tool_calls", [])
                ]
                if tool_calls:
                    messages.append(assistant_tool_message(round_record.get("assistant_text"), tool_calls))
                tool_results = round_record.get("tool_results", [])
                if tool_results:
                    messages.append(tool_results_message(tool_results))

            asst_msg = turn.get("assistant_text")
            if asst_msg:
                messages.append({"role": "assistant", "content": asst_msg})

        messages.append({"role": "user", "content": user_text})
        return messages

    def step(
        self,
        user_text: str,
        provider: Provider,
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> dict[str, Any]:
        turn_index = len(self.turns) + 1
        turn_record: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
            "pending_action_before": dict(self.pending_action) if self.pending_action else None,
            "pending_action_after": None,
        }

        # Check for explicit cancellation of pending action
        if self.pending_action and CANCEL_PATTERNS.search(user_text):
            cancelled_action = self.pending_action
            self.pending_action = None
            self.pending_clarification = None
            reply = f"Đã hủy yêu cầu: {cancelled_action.get('summary', 'thao tác')}. Tôi sẽ không thực hiện hành động này."
            turn_record.update({
                "status": "cancelled",
                "assistant_text": reply,
                "ended_at": now_iso(),
                "pending_action_after": None,
            })
            self.turns.append(turn_record)
            return turn_record

        messages = self.build_messages(user_text, system_prompt)
        working_messages = list(messages)
        rounds: list[dict[str, Any]] = []
        all_tool_events: list[dict[str, Any]] = []

        for round_index in range(1, self.max_tool_rounds + 1):
            response = provider.complete(working_messages, tools, model=self.model, temperature=0.0)
            calls = response.tool_calls
            round_record: dict[str, Any] = {
                "round": round_index,
                "assistant_text": response.text,
                "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
                "tool_results": [],
            }

            if not calls:
                rounds.append(round_record)
                turn_record.update({
                    "status": "answered",
                    "assistant_text": response.text or "",
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                    "ended_at": now_iso(),
                })
                break

            working_messages.append(assistant_tool_message(response.text, calls))
            non_clarification_events: list[dict[str, Any]] = []
            hit_clarification = False

            for call in calls:
                event = execute_tool_call(call)
                round_record["tool_results"].append(event)
                all_tool_events.append(event)
                result = event.get("result", {})

                # Track action creation states
                if call.name == "create_ticket":
                    if isinstance(result, dict):
                        if result.get("status") == "needs_confirmation":
                            # Ticket requires user confirmation; record pending payload
                            self.pending_action = {
                                "tool": "create_ticket",
                                "summary": call.args.get("summary"),
                                "priority": call.args.get("priority", "medium"),
                                "asset_id": call.args.get("asset_id", ""),
                            }
                        elif result.get("status") == "created":
                            # Action completed successfully, clear pending action
                            self.pending_action = None

                # Detect clarification
                if isinstance(result, dict) and result.get("awaiting_user"):
                    hit_clarification = True
                    self.pending_clarification = result
                    question = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                    rounds.append(round_record)
                    turn_record.update({
                        "status": "waiting_for_user",
                        "assistant_text": question,
                        "rounds": rounds,
                        "tool_events": all_tool_events,
                        "ended_at": now_iso(),
                    })
                    break

                non_clarification_events.append(event)

            if hit_clarification:
                break

            rounds.append(round_record)
            working_messages.append(tool_results_message(non_clarification_events))
        else:
            turn_record.update({
                "status": "max_tool_rounds",
                "assistant_text": f"Đã dừng sau {self.max_tool_rounds} lượt công cụ.",
                "rounds": rounds,
                "tool_events": all_tool_events,
                "ended_at": now_iso(),
            })

        turn_record["pending_action_after"] = dict(self.pending_action) if self.pending_action else None
        self.turns.append(turn_record)
        return turn_record

    def to_transcript_dict(self) -> dict[str, Any]:
        artifact_ver = self.get_artifact_version()
        return {
            "transcript_id": self.session_id,
            **artifact_version_dict(artifact_ver),
            "provider": self.provider_name,
            "model": self.model,
            "system_prompt": str(self.system_prompt_path),
            "tools": str(self.tools_path),
            "history_window": self.history_window,
            "max_tool_rounds": self.max_tool_rounds,
            "created_at": self.created_at,
            "updated_at": now_iso(),
            "turns": self.turns,
        }

    def save_transcript(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_transcript_dict()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

