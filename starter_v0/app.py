from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import streamlit as st

from conversation import ConversationSession
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

st.set_page_config(page_title="IT Helpdesk Assistant — Day04", page_icon="🛠️", layout="wide")


def init_session_state() -> None:
    if "session" not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
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
    )
    session.provider_name = provider_name

    default_models = {
        "gemini": "gemini-3.6-flash",
        "openrouter": "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-4-5-20251001",
    }
    model_name = st.text_input("Model", value=default_models.get(provider_name, ""))
    session.model = model_name or None

    version_label = st.selectbox("Artifact Version", options=["v3", "v2", "v1", "v0"], index=0)
    session.version = version_label

    art_ver = session.get_artifact_version()
    st.markdown("---")
    st.markdown(f"**Artifact Version:** `{art_ver.artifact_version}`")
    st.markdown(f"**Prompt SHA256:** `{art_ver.prompt_hash[:12]}...`")
    st.markdown(f"**Tools SHA256:** `{art_ver.tools_hash[:12]}...`")

    st.markdown("---")
    if session.pending_action:
        st.warning(f"⚠️ **Pending Action:** {session.pending_action.get('tool')}\n\n{session.pending_action.get('summary')}")
    else:
        st.info("Trạng thái: Sẵn sàng nhận yêu cầu.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reset Chat"):
            session.reset()
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

# Main Chat View
st.title("🛠️ IT Helpdesk AI Assistant — Northstar Labs")
st.caption("Trợ lý hỗ trợ kỹ thuật nội bộ Northstar Labs với cơ chế Tool Calling, bảo mật và lưu vết tương tác.")

# Display turn history
for turn in session.turns:
    with st.chat_message("user"):
        st.markdown(turn.get("user", ""))

    with st.chat_message("assistant"):
        # Display tool calls and tool results per round
        for r in turn.get("rounds", []):
            calls = r.get("tool_calls", [])
            results = r.get("tool_results", [])
            if calls:
                with st.expander(f"🔧 Round {r.get('round')}: {len(calls)} tool call(s)", expanded=False):
                    for call, event in zip(calls, results or [{}] * len(calls)):
                        st.markdown(f"**Tool:** `{call.get('name')}`")
                        st.code(json.dumps(call.get("args", {}), indent=2, ensure_ascii=False), language="json")
                        st.markdown("**Result:**")
                        st.code(json.dumps(event.get("result", {}), indent=2, ensure_ascii=False), language="json")

        asst_text = turn.get("assistant_text")
        if asst_text:
            st.markdown(asst_text)

        status = turn.get("status")
        if status == "waiting_for_user":
            st.info("ℹ️ Trợ lý đang chờ thêm thông tin từ bạn để xử lý tiếp.")
        elif status == "cancelled":
            st.warning("⛔ Thao tác đã được hủy bỏ thành công.")

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

            # Render newest turn response
            for r in turn_result.get("rounds", []):
                calls = r.get("tool_calls", [])
                results = r.get("tool_results", [])
                if calls:
                    with st.expander(f"🔧 Round {r.get('round')}: {len(calls)} tool call(s)", expanded=True):
                        for call, event in zip(calls, results or [{}] * len(calls)):
                            st.markdown(f"**Tool:** `{call.get('name')}`")
                            st.code(json.dumps(call.get("args", {}), indent=2, ensure_ascii=False), language="json")
                            st.markdown("**Result:**")
                            st.code(json.dumps(event.get("result", {}), indent=2, ensure_ascii=False), language="json")

            if turn_result.get("assistant_text"):
                st.markdown(turn_result["assistant_text"])

    except Exception as exc:
        st.error(f"Lỗi thực thi: {type(exc).__name__}: {str(exc)}")

