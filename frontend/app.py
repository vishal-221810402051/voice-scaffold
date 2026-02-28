import json
import requests
import streamlit as st
from typing import Any, Dict, Optional

st.set_page_config(page_title="Voice-Scaffold", layout="wide")

# ----------------------------
# Helpers
# ----------------------------
def http_post(url: str, json_body: Optional[dict] = None, files=None, params=None, timeout: int = 120):
    try:
        r = requests.post(url, json=json_body, files=files, params=params, timeout=timeout)
        return r
    except Exception as e:
        return None, str(e)

def http_get(url: str, timeout: int = 60):
    try:
        r = requests.get(url, timeout=timeout)
        return r
    except Exception as e:
        return None, str(e)

def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)

def show_response(r):
    if isinstance(r, tuple) and r[0] is None:
        st.error(f"Request failed: {r[1]}")
        return None
    if r is None:
        st.error("No response")
        return None
    try:
        data = r.json()
    except Exception:
        st.code(r.text)
        return None
    return data

def extract_detail_payload(data: dict) -> dict:
    # Our APIs sometimes return errors in HTTPException.detail
    # Swagger shows it nested; requests sees it as {"detail": {...}} sometimes.
    if isinstance(data, dict) and "detail" in data and isinstance(data["detail"], dict):
        return data["detail"]
    return data

# ----------------------------
# Sidebar: Backend + Project
# ----------------------------
st.sidebar.title("⚙️ Control")
backend_base = st.sidebar.text_input("Backend Base URL", value=st.session_state.get("backend_base", "http://127.0.0.1:8050"))
st.session_state["backend_base"] = backend_base.rstrip("/")

project_name = st.sidebar.text_input("Project Name", value=st.session_state.get("project_name", "crypto-stream-pipeline"))
st.session_state["project_name"] = project_name.strip()

colA, colB = st.sidebar.columns(2)
with colA:
    if st.button("🔄 Load Memory"):
        url = f"{st.session_state['backend_base']}/memory/{st.session_state['project_name']}"
        resp = http_get(url)
        data = show_response(resp)
        if data and data.get("ok"):
            st.session_state["memory_ast"] = data.get("ast")
            st.sidebar.success("Loaded AST from memory")
        else:
            st.session_state["memory_ast"] = None
            st.sidebar.warning("No stored AST or error")
with colB:
    if st.button("🧹 Reset Memory"):
        url = f"{st.session_state['backend_base']}/memory/{st.session_state['project_name']}"
        resp = http_post(url.replace("/memory/", "/memory/"), json_body=None)  # placeholder; delete uses requests.delete below
        try:
            r = requests.delete(url, timeout=30)
            data = show_response(r)
            if data and data.get("ok"):
                st.session_state["memory_ast"] = None
                st.sidebar.success("Memory reset")
        except Exception as e:
            st.sidebar.error(str(e))

st.sidebar.divider()

# ----------------------------
# Main Layout
# ----------------------------
st.title("🎙 Voice-Scaffold")
st.caption("Deterministic voice-to-infrastructure compiler (AST → validate → diff → generate → run)")

tab_voice, tab_transcript, tab_update, tab_run, tab_debug = st.tabs(
    ["1) Voice Compile", "2) Transcript Parse", "3) Update Flow", "4) Run Stack", "Debug"]
)

# ----------------------------
# TAB 1: Voice Compile (audio -> transcript -> AST)
# ----------------------------
with tab_voice:
    st.subheader("Voice → Transcript → AST")
    st.write("Uploads audio to Speechmatics, then parses transcript to Infra AST (OpenAI + fallback).")

    audio = st.file_uploader("Upload audio (wav/m4a/mp3)", type=["wav", "m4a", "mp3", "mp4", "aac"])
    lang = st.text_input("Language", value="en")

    if st.button("🎧 Voice Compile", disabled=(audio is None)):
        url = f"{st.session_state['backend_base']}/voice/compile"
        files = {"audio": (audio.name, audio.getvalue(), audio.type)}
        resp = http_post(url, files=files, params={"language": lang}, timeout=180)
        data = show_response(resp)
        if data:
            st.session_state["last_transcript"] = data.get("transcript")
            st.session_state["last_ast"] = data.get("ast")
            st.session_state["last_validation"] = data.get("validation")
            st.success("Voice compile complete")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Transcript**")
        st.text_area("", value=st.session_state.get("last_transcript", ""), height=180)
    with c2:
        st.markdown("**Validation**")
        st.code(pretty(st.session_state.get("last_validation", {})))

    st.markdown("**AST**")
    st.code(pretty(st.session_state.get("last_ast", {})))

# ----------------------------
# TAB 2: Transcript Parse (transcript -> AST)
# ----------------------------
with tab_transcript:
    st.subheader("Transcript → AST (No audio)")
    default_tx = st.session_state.get(
        "last_transcript",
        "Create a realtime data stack named crypto-stream-pipeline with Kafka, Spark streaming, DuckDB, and a Streamlit dashboard."
    )
    transcript = st.text_area("Transcript input", value=default_tx, height=140)

    if st.button("🧠 Parse Transcript"):
        url = f"{st.session_state['backend_base']}/parse"
        resp = http_post(url, json_body={"transcript": transcript}, timeout=120)
        data = show_response(resp)
        if data:
            st.session_state["last_transcript"] = transcript
            st.session_state["last_ast"] = data.get("ast")
            st.session_state["last_validation"] = data.get("validation")
            st.success("Parsed transcript to AST")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Validation**")
        st.code(pretty(st.session_state.get("last_validation", {})))
    with c2:
        st.markdown("**AST**")
        st.code(pretty(st.session_state.get("last_ast", {})))

# ----------------------------
# TAB 3: Update Flow (preview diff -> apply)
# ----------------------------
with tab_update:
    st.subheader("Incremental Update (Preview → Apply)")
    st.write("Uses memory + diff engine. Preview does not write files. Apply persists and regenerates scaffold.")

    st.markdown("**Current stored AST (Memory)**")
    mem_ast = st.session_state.get("memory_ast")
    st.code(pretty(mem_ast if mem_ast else {"note": "Click 'Load Memory' in sidebar."}))

    st.divider()

    update_tx = st.text_area(
        "Update instruction (transcript)",
        value="Change Kafka port to 19092 and keep everything else the same.",
        height=120
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔎 Preview Update"):
            url = f"{st.session_state['backend_base']}/update/preview/{st.session_state['project_name']}"
            resp = http_post(url, json_body={"transcript": update_tx}, timeout=120)
            data = show_response(resp)
            if data:
                st.session_state["preview_payload"] = data
                st.session_state["preview_new_ast"] = data.get("new_ast")
                st.session_state["preview_diff"] = data.get("diff", {}).get("summary")
                st.session_state["preview_validation"] = data.get("validation")
                st.success("Preview ready (no files written)")
    with col2:
        if st.button("✅ Apply Update (persist + regenerate)", disabled=("preview_new_ast" not in st.session_state)):
            url = f"{st.session_state['backend_base']}/update/apply/{st.session_state['project_name']}"
            resp = http_post(url, json_body={"new_ast": st.session_state.get("preview_new_ast")}, timeout=180)
            data = show_response(resp)
            if data:
                st.session_state["apply_result"] = data
                st.success("Applied update: memory saved + scaffold regenerated")
                # refresh memory view
                mem_url = f"{st.session_state['backend_base']}/memory/{st.session_state['project_name']}"
                mem_resp = http_get(mem_url)
                mem_data = show_response(mem_resp)
                if mem_data and mem_data.get("ok"):
                    st.session_state["memory_ast"] = mem_data.get("ast")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Diff Summary**")
        st.code(pretty(st.session_state.get("preview_diff", {})))
        st.markdown("**Validation**")
        st.code(pretty(st.session_state.get("preview_validation", {})))
    with c2:
        st.markdown("**Proposed New AST**")
        st.code(pretty(st.session_state.get("preview_new_ast", {})))

    st.markdown("**Apply Result**")
    st.code(pretty(st.session_state.get("apply_result", {})))

# ----------------------------
# TAB 4: Run Stack (up/logs/down)
# ----------------------------
with tab_run:
    st.subheader("Execution Control (docker compose)")
    st.write("Controls the generated project under /generated/<project_name> via backend execution layer.")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("🚀 Run Up"):
            url = f"{st.session_state['backend_base']}/run/up"
            resp = http_post(url, json_body={"project_name": st.session_state["project_name"]}, timeout=300)
            data = show_response(resp)
            if data:
                st.session_state["run_up"] = data
                st.success("docker compose up -d issued")
    with c2:
        tail = st.number_input("Logs tail", min_value=10, max_value=2000, value=200, step=10)
        if st.button("📜 Fetch Logs"):
            url = f"{st.session_state['backend_base']}/run/logs"
            resp = http_post(url, json_body={"project_name": st.session_state["project_name"], "tail": int(tail)}, timeout=120)
            data = show_response(resp)
            if data:
                st.session_state["run_logs"] = data
    with c3:
        if st.button("🛑 Run Down"):
            url = f"{st.session_state['backend_base']}/run/down"
            resp = http_post(url, json_body={"project_name": st.session_state["project_name"]}, timeout=300)
            data = show_response(resp)
            if data:
                st.session_state["run_down"] = data
                st.success("docker compose down issued")

    st.markdown("**Up result**")
    st.code(pretty(st.session_state.get("run_up", {})))

    st.markdown("**Logs**")
    logs_payload = st.session_state.get("run_logs", {})
    if logs_payload:
        st.text_area("stdout", value=logs_payload.get("stdout", ""), height=240)
        st.text_area("stderr", value=logs_payload.get("stderr", ""), height=120)
    else:
        st.info("No logs fetched yet.")

    st.markdown("**Down result**")
    st.code(pretty(st.session_state.get("run_down", {})))

# ----------------------------
# TAB 5: Debug
# ----------------------------
with tab_debug:
    st.subheader("Debug / State")
    st.write("Session state snapshot for troubleshooting demo behavior.")
    st.code(pretty({k: v for k, v in st.session_state.items() if k not in ["_is_running_with_streamlit"]}))
