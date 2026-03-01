import json
import io
import shutil
import requests
import streamlit as st
from typing import Any, Dict, Optional

# Optional audio deps can fail on Python 3.13 (audioop removed).
audiorecorder = None
AUDIORECORDER_IMPORT_ERROR = None
try:
    from audiorecorder import audiorecorder as _audiorecorder
    audiorecorder = _audiorecorder
except Exception as exc:
    AUDIORECORDER_IMPORT_ERROR = str(exc)

AudioSegment = None
try:
    from pydub import AudioSegment as _AudioSegment
    AudioSegment = _AudioSegment
except Exception:
    pass

st.set_page_config(page_title="Voice-Scaffold", layout="wide")

ffmpeg_path = shutil.which("ffmpeg")
ffprobe_path = shutil.which("ffprobe")

if AudioSegment is not None and ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
if AudioSegment is not None and ffprobe_path:
    AudioSegment.ffprobe = ffprobe_path

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

def inspect_audio_bytes(payload: bytes, source: str) -> Dict[str, Any]:
    header = payload[:12] if payload else b""
    return {
        "source": source,
        "size_bytes": len(payload) if payload is not None else 0,
        "header_ascii": header.decode("ascii", errors="replace"),
        "header_hex": header.hex(),
        "is_riff_wave": len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE",
    }

def speak(text: str):
    # Uses browser Web Speech API (no backend needed)
    st.components.v1.html(f"""
    <script>
    const msg = new SpeechSynthesisUtterance({json.dumps(text)});
    msg.rate = 1.0;
    msg.pitch = 1.0;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(msg);
    </script>
    """, height=0)

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
backend_base = st.sidebar.text_input("Backend Base URL", value=st.session_state.get("backend_base", "http://127.0.0.1:8888"))
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
    st.write("Record from microphone (recommended) or upload audio. Then compile to AST and generate docker-compose.yml.")

    lang = st.text_input("Language", value="en")
    st.markdown("### 🎤 Microphone")
    st.caption("Use `http://localhost:8503` and allow microphone access in your browser for reliable mic capture.")
    with st.expander("Mic permission checklist", expanded=False):
        st.markdown(
            "- Open this app on `http://localhost:8503` (localhost is treated as secure for mic access).\n"
            "- Click the browser lock icon and set **Microphone** to **Allow**.\n"
            "- After changing permission, refresh this page and record again.\n"
            "- If mic bytes are invalid, use **Upload Audio** as fallback."
        )

    audio_bytes = None
    mic_error = None
    mic_debug = None
    mic_invalid_reason = None
    recorded_file = None

    if audiorecorder is not None:
        try:
            audio_bytes = audiorecorder("Start recording", "Stop recording")
        except FileNotFoundError:
            mic_error = "Mic recording requires FFmpeg/ffprobe. Install FFmpeg or use Upload Audio (fallback)."
        except Exception as e:
            mic_error = f"Mic recording error: {e}"
    else:
        mic_error = (
            "Microphone recorder is unavailable in this Python environment "
            f"({AUDIORECORDER_IMPORT_ERROR or 'unknown import error'}). "
            "Use Upload Audio (fallback), or run with Python 3.12."
        )

    if audio_bytes is not None and hasattr(audio_bytes, "export"):
        try:
            wav_buffer = io.BytesIO()
            audio_bytes.export(wav_buffer, format="wav")
            wav_bytes = wav_buffer.getvalue()
            mic_debug = inspect_audio_bytes(wav_bytes, source="microphone")
            st.audio(wav_bytes, format="audio/wav")
            if mic_debug["size_bytes"] <= 44 or not mic_debug["is_riff_wave"]:
                mic_invalid_reason = "Mic audio captured, but WAV header/size looks invalid."
            else:
                # Force correct name + MIME for backend multipart upload.
                recorded_file = ("mic.wav", wav_bytes, "audio/wav")
                st.success("Mic audio captured. Click 'Voice Compile' to transcribe.")
        except Exception as e:
            mic_invalid_reason = f"Mic conversion to WAV failed: {e}"
    elif audio_bytes is not None and hasattr(audio_bytes, "tobytes") and len(audio_bytes) > 0:
        # Keep a diagnostic path if export API is unavailable.
        raw_bytes = audio_bytes.tobytes()
        mic_debug = inspect_audio_bytes(raw_bytes, source="microphone_raw")
        mic_invalid_reason = "Mic capture returned raw bytes without WAV export support."

    if mic_error:
        st.warning(mic_error)
    if mic_invalid_reason:
        st.warning(f"{mic_invalid_reason} Use Upload Audio fallback.")

    st.markdown("### 📁 Or Upload Audio")
    audio = st.file_uploader("Upload audio (wav/m4a/mp3)", type=["wav", "m4a", "mp3", "mp4", "aac"])
    upload_bytes = audio.getvalue() if audio is not None else b""
    upload_debug = inspect_audio_bytes(upload_bytes, source="upload") if audio is not None else None

    with st.expander("Audio payload debug", expanded=False):
        if mic_debug is not None:
            st.json(mic_debug)
        if upload_debug is not None:
            st.json(upload_debug)
        if mic_debug is None and upload_debug is None:
            st.caption("No audio payload captured yet.")

    compile_clicked = st.button("🎧 Voice Compile")

    if compile_clicked:
        url = f"{st.session_state['backend_base']}/voice/compile"

        if recorded_file is not None:
            files = {"audio": recorded_file}
            st.caption("Sending `microphone` audio payload (`audio/wav`) to backend.")
        elif audio is not None:
            if len(upload_bytes) == 0:
                st.error("Uploaded audio file is empty. Choose a different file.")
                st.stop()
            upload_mime = audio.type or ("audio/wav" if (audio.name or "").lower().endswith(".wav") else "application/octet-stream")
            files = {"audio": (audio.name, upload_bytes, upload_mime)}
            if mic_invalid_reason:
                st.warning("Microphone payload was invalid. Falling back to uploaded audio.")
            st.caption(f"Sending `upload` audio payload (`{upload_mime}`) to backend.")
        else:
            st.error("No audio provided. Record using mic or upload a file.")
            st.stop()

        resp = http_post(url, files=files, params={"language": lang}, timeout=180)
        data = show_response(resp)
        if data:
            st.session_state["last_transcript"] = data.get("transcript")
            st.session_state["last_ast"] = data.get("ast")
            st.session_state["last_validation"] = data.get("validation")
            st.success("Voice compile complete")
            if (data.get("validation") or {}).get("valid"):
                speak("Voice compiled. Architecture parsed and validated.")
            else:
                speak("Voice compiled, but validation failed. Please check the errors shown on screen.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Transcript**")
        st.text_area("Transcript", value=st.session_state.get("last_transcript", ""), height=180, label_visibility="collapsed")
    with c2:
        st.markdown("**Validation**")
        st.code(pretty(st.session_state.get("last_validation", {})))

    st.markdown("**AST**")
    st.code(pretty(st.session_state.get("last_ast", {})))

    st.divider()
    st.subheader("🚀 One-click: Save + Generate + Download docker-compose.yml")

    if st.button("⚡ Compile → Save Memory → Generate YAML", disabled=not st.session_state.get("last_ast")):
        ast = st.session_state["last_ast"]
        proj = st.session_state["project_name"]
        base = st.session_state["backend_base"]

        # 1) Save to memory
        mem_url = f"{base}/memory/{proj}"
        mem_resp = http_post(mem_url, json_body={"ast": ast}, timeout=60)
        mem_data = show_response(mem_resp)
        if not mem_data or not mem_data.get("ok"):
            st.error("Failed to save memory")
            speak("Failed to save memory.")
            st.stop()

        # 2) Generate scaffold
        gen_url = f"{base}/generate"
        gen_resp = http_post(gen_url, json_body=ast, timeout=120)
        gen_data = show_response(gen_resp)
        if not gen_data or not gen_data.get("ok"):
            st.error("Failed to generate project scaffold")
            speak("Failed to generate project scaffold.")
            st.stop()

        st.session_state["gen_result"] = gen_data
        st.success("Generated scaffold")
        speak("Docker compose file generated. You can download it now.")

    # If generation result exists, read compose and offer download
    gen_result = st.session_state.get("gen_result")
    if gen_result and gen_result.get("project_dir"):
        # Compose path is deterministic
        compose_path = gen_result["project_dir"] + "\\docker-compose.yml"
        try:
            with open(compose_path, "r", encoding="utf-8") as f:
                compose_text = f.read()
            st.download_button(
                label="⬇️ Download docker-compose.yml",
                data=compose_text,
                file_name="docker-compose.yml",
                mime="text/yaml",
            )
            st.code(compose_text, language="yaml")
        except Exception as e:
            st.warning(f"Could not read compose file: {e}")

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
            if (data.get("validation") or {}).get("valid"):
                speak("Transcript parsed and validation passed.")
            else:
                speak("Transcript parsed, but validation failed. Please check the errors.")

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
                speak("Preview complete. No files were written.")
    with col2:
        if st.button("✅ Apply Update (persist + regenerate)", disabled=("preview_new_ast" not in st.session_state)):
            url = f"{st.session_state['backend_base']}/update/apply/{st.session_state['project_name']}"
            resp = http_post(url, json_body={"new_ast": st.session_state.get("preview_new_ast")}, timeout=180)
            data = show_response(resp)
            if data:
                st.session_state["apply_result"] = data
                st.success("Applied update: memory saved + scaffold regenerated")
                speak("Update applied. Memory saved and scaffold regenerated.")
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
                speak("Stack start command sent.")
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
                speak("Stack stop command sent.")

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




