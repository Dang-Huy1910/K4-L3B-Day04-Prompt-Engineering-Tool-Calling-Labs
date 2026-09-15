from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from conversation import ConversationSession
from providers.base import ModelResponse, ToolCall

ROOT = Path(__file__).resolve().parents[1]


def test_conversation_session_cancellation():
    session = ConversationSession(
        session_id="test_cancel",
        version="v0",
        system_prompt_path=ROOT / "artifacts" / "system_prompt.md",
        tools_path=ROOT / "artifacts" / "tools.yaml",
        provider_name="mock",
    )
    # Set a pending action
    session.pending_action = {"tool": "create_ticket", "summary": "Fix VPN", "priority": "high"}

    mock_provider = MagicMock()
    # User says cancel
    result = session.step(
        user_text="Thôi hủy bỏ không tạo ticket nữa nhé",
        provider=mock_provider,
        tools=[],
        system_prompt="system prompt",
    )

    assert result["status"] == "cancelled"
    assert "Đã hủy" in result["assistant_text"]
    assert session.pending_action is None
    # Provider must not be called when cancelled
    mock_provider.complete.assert_not_called()


def test_conversation_session_pending_action_tracking():
    session = ConversationSession(
        session_id="test_action",
        version="v0",
        system_prompt_path=ROOT / "artifacts" / "system_prompt.md",
        tools_path=ROOT / "artifacts" / "tools.yaml",
        provider_name="mock",
    )

    # Provider requests create_ticket with confirmed=False
    mock_provider = MagicMock()
    mock_provider.complete.return_value = ModelResponse(
        text="Tôi sẽ tạo ticket.",
        tool_calls=[
            ToolCall(
                name="create_ticket",
                args={"summary": "Hỏng chuột máy tính", "priority": "low", "confirmed": False},
            )
        ],
    )

    result = session.step(
        user_text="Tạo ticket giúp tôi",
        provider=mock_provider,
        tools=[],
        system_prompt="system prompt",
    )

    assert session.pending_action is not None
    assert session.pending_action["tool"] == "create_ticket"
    assert session.pending_action["summary"] == "Hỏng chuột máy tính"


def test_conversation_transcript_generation(tmp_path):
    session = ConversationSession(
        session_id="test_transcript",
        version="v0",
        system_prompt_path=ROOT / "artifacts" / "system_prompt.md",
        tools_path=ROOT / "artifacts" / "tools.yaml",
        provider_name="mock",
    )

    mock_provider = MagicMock()
    mock_provider.complete.return_value = ModelResponse(
        text="Xin chào, tôi là IT Helpdesk.",
        tool_calls=[],
    )

    session.step(
        user_text="Xin chào",
        provider=mock_provider,
        tools=[],
        system_prompt="system prompt",
    )

    out_file = tmp_path / "test.transcript.json"
    session.save_transcript(out_file)
    assert out_file.exists()

    data = session.to_transcript_dict()
    assert data["transcript_id"] == "test_transcript"
    assert len(data["turns"]) == 1
    assert data["turns"][0]["user"] == "Xin chào"
    assert data["turns"][0]["assistant_text"] == "Xin chào, tôi là IT Helpdesk."

