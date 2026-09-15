from __future__ import annotations

from typing import Any


def ask_user(
    question: str = "",
    response_type: str = "text",
    options: list[str] | None = None,
    action: str = "",
    action_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "tool": "clarify",
        "question": question,
        "response_type": response_type,
        "options": options or [],
        "awaiting_user": True,
    }
    if action:
        result["action"] = action
        result["action_args"] = action_args or {}
    return result
