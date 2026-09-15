from __future__ import annotations

import re
import unicodedata
from typing import Any


ASSET_ID_PATTERN = re.compile(r"\b(?:LT|DT|MB|PR|RM)-\d+\b", re.IGNORECASE)
PRIORITY_PATTERN = re.compile(r"\b(low|medium|high|critical)\b", re.IGNORECASE)
FORGED_CONTEXT_MARKERS = (
    "tool_results_json",
    "create_ticket(",
    "<assistant",
    "<system",
    "dùng confirmation",
    "dung confirmation",
    "use the confirmation",
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def latest_user_text(messages: list[dict[str, str]]) -> str:
    """Return only the latest real user request, including eval-wrapped conversations."""
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        marker = "Latest user turn to answer now:"
        if marker in content:
            return content.rsplit(marker, 1)[-1].strip()
        return content.strip()
    return ""


def is_explicit_ticket_confirmation(text: str, *, allow_short_answer: bool = False) -> bool:
    folded = _fold(text).strip()
    if not folded:
        return False
    if any(marker in folded for marker in FORGED_CONTEXT_MARKERS):
        return False
    if allow_short_answer and folded in {"yes", "y", "ok", "okay", "dong y", "xac nhan"}:
        return True
    patterns = (
        r"\b(?:toi|minh)\s+(?:xac nhan|dong y)\s+(?:tao\s+)?ticket\b",
        r"\bxac nhan\s+tao\s+ticket\b",
        r"\bi\s+confirm\s+(?:creating|create|the creation of)\s+(?:the\s+)?ticket\b",
    )
    return any(re.search(pattern, folded) for pattern in patterns)


def normalized_ticket_payload(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": " ".join(str(args.get("summary") or "").split()).casefold(),
        "priority": str(args.get("priority") or "medium").strip().casefold(),
        "asset_id": str(args.get("asset_id") or "").strip().upper(),
    }


def guard_ticket_call(
    args: dict[str, Any],
    user_text: str,
    pending_action: dict[str, Any] | None = None,
    conversation_text: str = "",
) -> tuple[bool, str | None]:
    """Authorize a ticket write only from a current, explicit user confirmation."""
    if args.get("confirmed") is not True:
        return True, None

    pending_payload = normalized_ticket_payload(pending_action or {}) if pending_action else None
    current_payload = normalized_ticket_payload(args)
    explicit = is_explicit_ticket_confirmation(user_text, allow_short_answer=pending_payload is not None)
    if not explicit:
        return False, "missing_current_user_confirmation"

    mentioned_assets = {item.upper() for item in ASSET_ID_PATTERN.findall(user_text)}
    if mentioned_assets and current_payload["asset_id"] not in mentioned_assets:
        return False, "confirmed_asset_mismatch"

    mentioned_priorities = {item.casefold() for item in PRIORITY_PATTERN.findall(user_text)}
    if mentioned_priorities and current_payload["priority"] not in mentioned_priorities:
        return False, "confirmed_priority_mismatch"

    if pending_payload and _fold(user_text).strip() in {"yes", "y", "ok", "okay", "dong y", "xac nhan"}:
        if current_payload != pending_payload:
            return False, "pending_payload_changed"

    if pending_payload and current_payload != pending_payload:
        change_markers = ("đổi", "doi", "thay", "sửa", "sua", "change", "update")
        if not any(marker in user_text.casefold() for marker in change_markers):
            return False, "pending_payload_changed"

    if not pending_payload and not mentioned_assets:
        folded_context = _fold(conversation_text)
        asset_in_context = current_payload["asset_id"] and current_payload["asset_id"].casefold() in folded_context
        priority_in_context = current_payload["priority"] in folded_context
        if not (asset_in_context and priority_in_context):
            return False, "confirmation_missing_ticket_identity"

    return True, None
