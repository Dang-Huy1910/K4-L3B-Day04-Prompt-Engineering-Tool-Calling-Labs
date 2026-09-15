from __future__ import annotations

from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_import_smoke():
    app_path = ROOT / "app.py"
    assert app_path.exists()
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    assert not app.exception
    assert any(title.value == "Northstar Service Desk" for title in app.title)
    assert {box.label for box in app.selectbox} == {"Provider", "Artifact Version"}
    initial_artifact = next(item.value for item in app.markdown if "Artifact Version" in item.value)
    app.selectbox[1].select("v0").run()
    v0_artifact = next(item.value for item in app.markdown if "Artifact Version" in item.value)
    assert initial_artifact != v0_artifact
    assert "st.download_button" in app_path.read_text(encoding="utf-8")
