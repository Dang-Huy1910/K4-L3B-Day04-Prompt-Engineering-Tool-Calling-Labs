from __future__ import annotations

import pytest
from tools.check_warranty.tool import check_warranty


def test_check_warranty_active():
    res = check_warranty(asset_id="LT-204", as_of_date="2026-09-15")
    assert res["tool"] == "check_warranty"
    assert res["status"] == "active"
    assert res["is_active"] is True
    assert res["asset_id"] == "LT-204"
    assert res["tier"] == "Premier Support"
    assert res["on_site_service"] is True
    assert res["rma_eligible"] is True


def test_check_warranty_expired():
    # MB-012 ended on 2026-03-21, as of 2026-09-15 it is expired
    res = check_warranty(asset_id="MB-012", as_of_date="2026-09-15")
    assert res["tool"] == "check_warranty"
    assert res["status"] == "expired"
    assert res["is_active"] is False
    assert res["asset_id"] == "MB-012"


def test_check_warranty_not_found():
    res = check_warranty(asset_id="LT-999")
    assert res["tool"] == "check_warranty"
    assert res["error"] == "warranty_not_found"


def test_check_warranty_invalid_format():
    res = check_warranty(asset_id="xyz123")
    assert res["tool"] == "check_warranty"
    assert res["error"] == "invalid_asset_id_format"


def test_check_warranty_missing_id():
    res = check_warranty(asset_id="")
    assert res["tool"] == "check_warranty"
    assert res["error"] == "missing_asset_id"


def test_check_warranty_type_safety():
    res = check_warranty(asset_id=None)  # type: ignore
    assert res["tool"] == "check_warranty"
    assert res["error"] == "invalid_input_type"

