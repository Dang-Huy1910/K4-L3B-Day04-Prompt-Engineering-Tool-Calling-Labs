from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conversation import ConversationSession
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools

load_lab_env(ROOT)
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"


def run_scenario(
    name: str,
    turns: list[str],
    provider_name: str,
    model: str | None,
    version: str,
    system_prompt_path: Path,
    tools_path: Path,
) -> Path:
    session = ConversationSession(
        session_id=f"live_{name}",
        version=version,
        system_prompt_path=system_prompt_path,
        tools_path=tools_path,
        provider_name=provider_name,
        model=model,
    )
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    tools = to_openai_tools(declarations)
    provider = make_provider(provider_name)

    print(f"\n--- Running Scenario: {name} ---")
    for idx, user_text in enumerate(turns, 1):
        print(f"Turn {idx} User: {user_text}")
        result = session.step(
            user_text=user_text,
            provider=provider,
            tools=tools,
            system_prompt=system_prompt,
        )
        print(f"Turn {idx} Status: {result.get('status')}")
        print(f"Turn {idx} Assistant: {result.get('assistant_text')[:100]}...")

    out_file = TRANSCRIPTS_DIR / f"{name}.transcript.json"
    session.save_transcript(out_file)
    print(f"Saved: {out_file}")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate canonical transcripts for Day04 scenarios.")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", default="v3")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    args = parser.parse_args()

    scenarios = {
        "scenario_normal": [
            "Kiểm tra trạng thái dịch vụ VPN production giúp mình.",
        ],
        "scenario_clarify": [
            "Máy tính của tôi không vào được Wi-Fi công ty, hỗ trợ tôi với.",
            "Mã máy tính của tôi là LT-240.",
        ],
        "scenario_correction_cancel": [
            "Tạo ticket giúp tôi: Màn hình laptop LT-204 bị sọc ngang, ưu tiên cao nhé.",
            "Thôi khỏi tạo ticket, tôi vừa cắm lại cáp HDMI thì màn hình hết sọc rồi, hủy lệnh tạo ticket đi.",
        ],
        "scenario_write_action": [
            "Tạo ticket sự cố lỗi bàn phím cho laptop LT-204, priority high.",
            "Tôi xác nhận tạo ticket với nội dung lỗi bàn phím cho laptop LT-204, priority high.",
        ],
        "scenario_bonus_warranty": [
            "Kiểm tra bảo hành và tính đủ điều kiện RMA của laptop LT-204 giúp mình.",
            "Kiểm tra tiếp bảo hành của điện thoại MB-012 xem còn hạn không nhé.",
        ],
    }

    for name, turns in scenarios.items():
        run_scenario(
            name=name,
            turns=turns,
            provider_name=args.provider,
            model=args.model,
            version=args.version,
            system_prompt_path=args.system_prompt,
            tools_path=args.tools,
        )


if __name__ == "__main__":
    main()

