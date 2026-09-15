from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from conversation import ConversationSession
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"

def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive IT Helpdesk Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Student-chosen artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5, help="Keep the last N user/assistant pairs in context.")
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(args.tools)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(args.version),
        safe_slug(args.provider),
        timestamp,
    ])
    transcript_path = args.transcripts_dir / f"{transcript_id}.transcript.json"
    session = ConversationSession(
        session_id=transcript_id,
        version=args.version,
        system_prompt_path=args.system_prompt,
        tools_path=args.tools,
        provider_name=args.provider,
        model=selected_model,
        history_window=args.history_window,
        max_tool_rounds=args.max_tool_rounds,
    )

    print(f"IT Helpdesk Agent chat. artifact_version={session.get_artifact_version().artifact_version}")
    print("Type /exit to stop.")

    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            break

        result = session.step(user_text, provider, openai_tools, system_prompt)
        print(f"\nAgent> {result['assistant_text']}")
        if result.get("status") == "provider_error":
            print(f"ERROR> {result.get('error')}")
        session.save_transcript(transcript_path)
        print(f"Transcript saved: {transcript_path}")

    session.save_transcript(transcript_path)
    print(f"Final transcript: {transcript_path}")


if __name__ == "__main__":
    main()
