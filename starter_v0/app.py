from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import streamlit as st

from conversation import ConversationSession
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

st.set_page_config(page_title="Northstar Service Desk", page_icon="🛠️", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #0b0f17; color: #e5e7eb; }
    [data-testid="stSidebar"] { background: #111827; border-right: 1px solid rgba(255,255,255,.08); }
    h1, h2, h3 { letter-spacing: -0.02em; }
    code { font-variant-numeric: tabular-nums; }
    [data-testid="stChatMessage"] { border: 1px solid rgba(255,255,255,.08); background: #111827; }
    .trace-label { color: #94a3b8; font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    </style>
    """,
    unsafe_allow_html=True,
)


def artifact_paths(version: str) -> tuple[Path, Path]:
    if version == "v3":
        return ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml"
    version_dir = ARTIFACTS_DIR / "versions" / version
    return version_dir / "system_prompt.md", version_dir / "tools.yaml"


def available_versions() -> list[str]:
    versions: list[str] = []
    for version in ("v3", "v2", "v1", "v0"):
        prompt_path, tools_path = artifact_paths(version)
        if prompt_path.exists() and tools_path.exists():
            versions.append(version)
    return versions


def render_round(round_record: dict) -> None:
    calls = round_record.get("tool_calls", [])
    results = round_record.get("tool_results", [])
    if not calls:
        return
    has_error = any((event.get("result") or {}).get("error") for event in results)
    state_icon = "⚠️" if has_error else "✓"
    state_label = "ERROR" if has_error else "SUCCESS"
    with st.expander(
        f"{state_icon} Round {round_record.get('round')} · {len(calls)} tool call(s) · {state_label}",
        expanded=has_error,
    ):
        for index, call in enumerate(calls):
            event = results[index] if index < len(results) else {}
            st.markdown(f"<div class='trace-label'>Action · {call.get('name')}</div>", unsafe_allow_html=True)
            args_tab, result_tab = st.tabs(["Input", "Result / error"])
            with args_tab:
                st.json(call.get("args", {}), expanded=True)
            with result_tab:
                st.json(event.get("result", {"error": "missing_tool_result"}), expanded=True)


def init_session_state() -> None:
    if "session" not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        st.session_state.session = ConversationSession(
            session_id=f"ui_{timestamp}",
            version="v3",
            system_prompt_path=ARTIFACTS_DIR / "system_prompt.md",
            tools_path=ARTIFACTS_DIR / "tools.yaml",
            provider_name="gemini",
            model="gemini-3.6-flash",
        )
    if "transcript_saved" not in st.session_state:
        st.session_state.transcript_saved = None


init_session_state()
session: ConversationSession = st.session_state.session

# Sidebar controls
with st.sidebar:
    st.title("⚙️ Cấu hình Agent")
    provider_name = st.selectbox(
        "Provider",
        options=["gemini", "openrouter", "openai", "anthropic"],
        index=0,
        disabled=bool(session.turns),
        help="Reset chat before changing provider so the transcript has one execution context.",
    )
    session.provider_name = provider_name

    default_models = {
        "gemini": "gemini-3.6-flash",
        "openrouter": "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-4-5-20251001",
    }
    model_name = st.text_input(
        "Model",
        value=default_models.get(provider_name, ""),
        disabled=bool(session.turns),
    )
    session.model = model_name or None

    versions = available_versions()
    version_label = st.selectbox(
        "Artifact Version",
        options=versions,
        index=versions.index(session.version) if session.version in versions else 0,
        disabled=bool(session.turns),
        help="Reset chat before changing artifacts so one transcript never mixes versions.",
    )
    session.version = version_label
    session.system_prompt_path, session.tools_path = artifact_paths(version_label)

    art_ver = session.get_artifact_version()
    st.markdown("---")
    st.markdown(f"**Artifact Version:** `{art_ver.artifact_version}`")
    st.markdown(f"**Prompt SHA256:** `{art_ver.prompt_hash[:12]}...`")
    st.markdown(f"**Tools SHA256:** `{art_ver.tools_hash[:12]}...`")

    st.markdown("---")
    if session.pending_action:
        st.warning(f"⚠️ **REVIEW REQUIRED · {session.pending_action.get('tool')}**\n\n{session.pending_action.get('summary')}")
    else:
        st.info("Trạng thái: Sẵn sàng nhận yêu cầu.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reset Chat"):
            del st.session_state.session
            st.session_state.transcript_saved = None
            st.rerun()
    with col2:
        if st.button("💾 Lưu Transcript"):
            out_path = TRANSCRIPTS_DIR / f"{session.session_id}.transcript.json"
            session.save_transcript(out_path)
            st.session_state.transcript_saved = str(out_path)
            st.success(f"Đã lưu: {out_path.name}")

    if st.session_state.transcript_saved:
        st.caption(f"File: `{st.session_state.transcript_saved}`")

    transcript_json = json.dumps(session.to_transcript_dict(), ensure_ascii=False, indent=2)
    st.download_button(
        "↓ Download transcript JSON",
        data=transcript_json,
        file_name=f"{session.session_id}.transcript.json",
        mime="application/json",
        use_container_width=True,
    )

# Main Chat View
st.title("Northstar Service Desk")
st.caption("Internal support console · tool calls, evidence, and write-action review in one trace.")

# Display turn history
for turn in session.turns:
    with st.chat_message("user"):
        st.markdown(turn.get("user", ""))

    with st.chat_message("assistant"):
        for r in turn.get("rounds", []):
            render_round(r)

        asst_text = turn.get("assistant_text")
        if asst_text:
            st.markdown(asst_text)

        status = turn.get("status")
        if status == "waiting_for_user":
            st.info("ℹ️ Trợ lý đang chờ thêm thông tin từ bạn để xử lý tiếp.")
        elif status == "cancelled":
            st.warning("⛔ Thao tác đã được hủy bỏ thành công.")
        elif status == "provider_error":
            st.error(f"Provider error · {turn.get('error', 'unknown error')}")

# Chat input
if prompt := st.chat_input("Nhập câu hỏi hoặc yêu cầu hỗ trợ IT..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        system_prompt = session.system_prompt_path.read_text(encoding="utf-8")
        declarations = load_tool_declarations(session.tools_path)
        openai_tools = to_openai_tools(declarations)
        provider = make_provider(session.provider_name)

        with st.chat_message("assistant"):
            with st.spinner("Đang suy luận và kiểm tra công cụ..."):
                turn_result = session.step(
                    user_text=prompt,
                    provider=provider,
                    tools=openai_tools,
                    system_prompt=system_prompt,
                )

            for r in turn_result.get("rounds", []):
                render_round(r)

            if turn_result.get("assistant_text"):
                st.markdown(turn_result["assistant_text"])
            if turn_result.get("status") == "provider_error":
                st.error(f"Provider error · {turn_result.get('error', 'unknown error')}")

    except Exception as exc:
        st.error(f"Lỗi thực thi: {type(exc).__name__}: {str(exc)}")
