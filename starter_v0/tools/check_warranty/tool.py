from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from tools._shared import ROOT, err

WARRANTY_FILE = ROOT / "helpdesk_data" / "warranties.json"
ASSET_ID_PATTERN = re.compile(r"^(?:LT|DT|MB|PR|RM)-\d+$", re.IGNORECASE)


def check_warranty(asset_id: str = "", as_of_date: str = "") -> dict[str, Any]:
    """Check device hardware warranty status, coverage tier, and RMA eligibility.
    
    Deterministic local lookup using simulated company warranty records.
    """
    if not isinstance(asset_id, str):
        return {"tool": "check_warranty", "error": "invalid_input_type"}
    if not isinstance(as_of_date, str):
        return {"tool": "check_warranty", "error": "invalid_as_of_date_type"}

    normalized_id = asset_id.strip().upper()
    if not normalized_id:
        return {"tool": "check_warranty", "error": "missing_asset_id"}

    if not ASSET_ID_PATTERN.fullmatch(normalized_id):
        return {
            "tool": "check_warranty",
            "asset_id": normalized_id,
            "error": "invalid_asset_id_format",
            "message": "Asset ID must follow pattern LT-xxx, DT-xxx, MB-xxx, PR-xxx, or RM-xxx.",
        }

    try:
        data = json.loads(WARRANTY_FILE.read_text(encoding="utf-8"))
        reference_date = (as_of_date or data.get("as_of_date") or "").strip()
        try:
            reference_day = date.fromisoformat(reference_date)
        except ValueError:
            return {
                "tool": "check_warranty",
                "asset_id": normalized_id,
                "error": "invalid_as_of_date",
                "message": "as_of_date must use ISO YYYY-MM-DD format.",
            }
        warranty_entry = next((w for w in data["warranties"] if w["asset_id"] == normalized_id), None)

        if not warranty_entry:
            return {
                "tool": "check_warranty",
                "asset_id": normalized_id,
                "error": "warranty_not_found",
                "message": f"No warranty contract record found for asset {normalized_id}.",
            }

        start_date = warranty_entry["start_date"]
        end_date = warranty_entry["end_date"]
        start_day = date.fromisoformat(start_date)
        end_day = date.fromisoformat(end_date)
        is_active = start_day <= reference_day <= end_day
        if reference_day < start_day:
            status = "not_started"
        elif reference_day > end_day:
            status = "expired"
        else:
            status = "active"

        return {
            "tool": "check_warranty",
            "asset_id": normalized_id,
            "model": warranty_entry["model"],
            "status": status,
            "is_active": is_active,
            "tier": warranty_entry["tier"],
            "provider": warranty_entry["provider"],
            "start_date": start_date,
            "end_date": end_date,
            "as_of_date": reference_date,
            "on_site_service": is_active and warranty_entry.get("on_site_service", False),
            "rma_eligible": is_active and warranty_entry.get("rma_eligible", False),
            "accidental_damage": is_active and warranty_entry.get("accidental_damage", False),
            "source": "Northstar Enterprise Asset Warranty Registry",
        }
    except Exception as exc:
        return err("check_warranty", exc)
