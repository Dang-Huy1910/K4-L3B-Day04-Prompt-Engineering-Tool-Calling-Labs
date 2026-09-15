from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from tools.check_service_status.tool import check_service_status
from tools.clarify.tool import ask_user
from tools.create_ticket.tool import create_ticket
from tools.create_ticket import tool as create_ticket_mod
from tools.format_incident_report.tool import format_incident_report
from tools.inspect_device.tool import inspect_device
from tools.lookup_user.tool import lookup_user
from tools.policy.tool import search_company_policy
from tools.search_device_info.tool import search_device_info
from tools.search_kb.tool import search_kb


def test_clarify_contract():
    res = ask_user(question="Mã máy của bạn là gì?", response_type="text")
    assert res["tool"] == "clarify"
    assert res["question"] == "Mã máy của bạn là gì?"
    assert res["awaiting_user"] is True


def test_check_service_status_contract():
    res = check_service_status(service="vpn", environment="production")
    assert res["tool"] == "check_service_status"
    assert res["service"] == "vpn"
    assert res["environment"] == "production"
    assert "status" in res

    not_found = check_service_status(service="unknown_service")
    assert not_found["error"] == "not_found"


def test_inspect_device_contract():
    res = inspect_device(asset_id="LT-204", check="network")
    assert res["tool"] == "inspect_device"
    assert res["asset_id"] == "LT-204"
    assert "device" in res
    assert "network" in res["diagnostics"]

    not_found = inspect_device(asset_id="LT-999")
    assert not_found["error"] == "asset_not_found"


def test_lookup_user_contract():
    res = lookup_user(employee_id="EMP-1001")
    assert res["tool"] == "lookup_user"
    assert res["employee"]["employee_id"] == "EMP-1001"

    not_found = lookup_user(employee_id="EMP-9999")
    assert not_found["error"] == "employee_not_found"


def test_policy_search_contract():
    res = search_company_policy(query="VPN password policy", policy_area="access_control")
    assert res["tool"] == "search_company_policy"
    assert "results" in res
    assert res["trust_boundary"] != ""


def test_search_kb_contract():
    res = search_kb(query="Outlook email", category="email")
    assert res["tool"] == "search_kb"
    assert "results" in res
    assert res["trust_boundary"] != ""


def test_format_incident_report_contract():
    findings = [{"label": "VPN Check", "detail": "AUTH_TIMEOUT", "source": "inspect_device"}]
    res = format_incident_report(findings=findings, template="brief", incident_title="VPN Issue")
    assert res["tool"] == "format_incident_report"
    assert res["finding_count"] == 1
    assert "VPN Issue" in res["markdown"]


def test_create_ticket_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(create_ticket_mod, "TICKET_DIR", tmp_path)

    # 1. Unconfirmed ticket must fail
    res_unconfirmed = create_ticket(summary="VPN issue", priority="medium", confirmed=False)
    assert res_unconfirmed["status"] == "needs_confirmation"

    # 2. Sensitive credential leak must be blocked
    res_sensitive = create_ticket(summary="Reset password: MySecret123!", confirmed=True)
    assert res_sensitive["error"] == "restricted_sensitive_data"

    # 3. Valid confirmed ticket should write to tmp_path
    res_valid = create_ticket(summary="VPN auth timeout", priority="high", asset_id="LT-204", confirmed=True)
    assert res_valid["status"] == "created"
    assert "ticket_id" in res_valid
    ticket_file = tmp_path / f"{res_valid['ticket_id']}.json"
    assert ticket_file.exists()


def test_search_device_info_isolation(monkeypatch):
    # 1. Blocks internal identifiers without network call
    res_leak = search_device_info(manufacturer="Lenovo", model="ThinkPad LT-204")
    assert res_leak["error"] == "restricted_internal_identifier"

    # 2. Mocked Tavily call without live API key
    monkeypatch.setenv("TAVILY_API_KEY", "mock-tavily-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "ThinkPad T14 Gen 4 Specs",
                "url": "https://psref.lenovo.com/Product/ThinkPad_T14_Gen_4",
                "content": "Official specs for ThinkPad T14 Gen 4",
                "score": 0.95,
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        res = search_device_info(manufacturer="Lenovo", model="ThinkPad T14 Gen 4", query_type="specs")
        assert res["tool"] == "search_device_info"
        assert len(res["items"]) == 1
        assert res["items"][0]["source"] == "psref.lenovo.com"
