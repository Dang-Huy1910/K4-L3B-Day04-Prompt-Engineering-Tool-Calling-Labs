from __future__ import annotations

import json
from pathlib import Path

from run_eval import ALLOWED_CASE_FAILURE_TYPES
from tools import TOOL_FUNCTIONS, load_tool_declarations

ROOT = Path(__file__).resolve().parents[1]
GROUP_FILE = ROOT / "data" / "eval_group.json"
TOOLS_FILE = ROOT / "artifacts" / "tools.yaml"


def test_eval_group_schema_and_counts():
    data = json.loads(GROUP_FILE.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) == 10, f"Expected exactly 10 cases, got {len(cases)}"

    single_turns = [c for c in cases if "turns" not in c]
    multi_turns = [c for c in cases if "turns" in c]
    assert len(single_turns) == 5, f"Expected 5 single-turn cases, got {len(single_turns)}"
    assert len(multi_turns) == 5, f"Expected 5 multi-turn cases, got {len(multi_turns)}"

    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), f"Duplicate case IDs found: {ids}"

    for c in cases:
        assert c["phase"] == "B", f"Case {c['id']} must have phase 'B'"
        assert c["failure_type"] in ALLOWED_CASE_FAILURE_TYPES, (
            f"Case {c['id']} invalid failure_type: {c['failure_type']}"
        )
        assert "expect" in c, f"Case {c['id']} missing expect block"
        assert "metadata" in c and "what_it_tests" in c["metadata"], (
            f"Case {c['id']} missing metadata.what_it_tests"
        )


def test_eval_group_expected_tools_validity():
    data = json.loads(GROUP_FILE.read_text(encoding="utf-8"))
    cases = data["cases"]
    declared_tools = {t["name"] for t in load_tool_declarations(TOOLS_FILE)}
    implemented_tools = set(TOOL_FUNCTIONS)

    for c in cases:
        expect = c["expect"]
        if expect.get("no_tool"):
            continue
        for call in expect.get("tool_calls", []):
            tool_name = call["name"]
            assert tool_name in declared_tools, (
                f"Case {c['id']}: expected tool {tool_name!r} not declared in tools.yaml"
            )
            assert tool_name in implemented_tools, (
                f"Case {c['id']}: expected tool {tool_name!r} not in TOOL_FUNCTIONS"
            )

