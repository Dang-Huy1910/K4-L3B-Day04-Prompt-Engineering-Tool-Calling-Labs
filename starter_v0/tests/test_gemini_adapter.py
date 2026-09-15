from __future__ import annotations

from unittest.mock import MagicMock, patch
from google.genai import types
from providers.gemini_provider import GeminiProvider, _is_retryable_provider_error


def test_daily_quota_error_is_not_retried():
    error = RuntimeError("429 RESOURCE_EXHAUSTED quota GenerateRequestsPerDayPerProjectPerModel")
    assert _is_retryable_provider_error(error) is False
    assert _is_retryable_provider_error(RuntimeError("503 UNAVAILABLE")) is True


def test_gemini_provider_tool_choice_required():
    provider = GeminiProvider()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_service_status",
                "description": "Check service status",
                "parameters": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            },
        }
    ]
    messages = [{"role": "user", "content": "Check VPN status"}]

    mock_resp = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_func_call = MagicMock()
    mock_func_call.name = "check_service_status"
    mock_func_call.args = {"service": "vpn"}
    mock_part.function_call = mock_func_call
    mock_part.text = None
    mock_candidate.content.parts = [mock_part]
    mock_resp.candidates = [mock_candidate]
    mock_resp.function_calls = []

    with patch("os.getenv", return_value="dummy-key"), \
         patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = provider.complete(messages, tools, tool_choice="required")
        assert len(res.tool_calls) == 1
        assert res.tool_calls[0].name == "check_service_status"
        assert res.tool_calls[0].args == {"service": "vpn"}

        # Verify tool_config mode was ANY
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        config = call_kwargs["config"]
        assert config.tool_config.function_calling_config.mode == types.FunctionCallingConfigMode.ANY


def test_gemini_provider_tool_choice_none():
    provider = GeminiProvider()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_service_status",
                "description": "Check service status",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    messages = [{"role": "user", "content": "Hello"}]

    mock_resp = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Hello! How can I help you?"
    mock_candidate.content.parts = [mock_part]
    mock_resp.candidates = [mock_candidate]
    mock_resp.function_calls = []

    with patch("os.getenv", return_value="dummy-key"), \
         patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = provider.complete(messages, tools, tool_choice="none")
        assert len(res.tool_calls) == 0
        assert res.text == "Hello! How can I help you?"

        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        config = call_kwargs["config"]
        assert config.tool_config.function_calling_config.mode == types.FunctionCallingConfigMode.NONE
