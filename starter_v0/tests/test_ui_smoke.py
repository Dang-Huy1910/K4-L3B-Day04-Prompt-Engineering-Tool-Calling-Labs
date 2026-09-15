from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_import_smoke():
    app_path = ROOT / "app.py"
    assert app_path.exists()
    spec = importlib.util.spec_from_file_location("app", app_path)
    assert spec is not None
    assert spec.loader is not None

