# Voice Scaffold

Voice Scaffold is a local full-stack app that converts architecture intent (voice or text) into a validated infrastructure AST, generates scaffolded project files, and can run generated stacks with Docker Compose.

This repository contains:
- A FastAPI backend (`backend/`)
- A Streamlit frontend (`frontend/`)
- Generated project output directory (`generated/`)
- Helper scripts (`scripts/`)

## What You Need

Required:
- Git
- Python 3.12 (recommended for best microphone compatibility)
- Windows PowerShell (commands below are for PowerShell)

Optional but recommended:
- FFmpeg (for microphone/audio tooling)
- Docker Desktop (only needed for `Run Up / Run Down / Logs` features)

API keys:
- `SPEECHMATICS_API_KEY` is required for voice transcription endpoints.
- `OPENAI_API_KEY` is optional for richer transcript parsing (backend falls back to a deterministic parser when unavailable).

## Quick Start (Windows)

Run these from the repository root.

### 1) Clone

```powershell
git clone <your-repo-url>
cd voice-scaffold
$REPO = (Get-Location).Path
```

### 2) Set up backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create `backend\.env`:

```env
SPEECHMATICS_API_KEY=your_speechmatics_key_here
OPENAI_API_KEY=your_openai_key_here
```

Start backend:

```powershell
uvicorn app.main:app --reload --port 8888
```

Verify:
- http://127.0.0.1:8888/
- http://127.0.0.1:8888/docs

### 3) Set up frontend

Open a second PowerShell terminal:

```powershell
cd "$REPO\frontend"
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start frontend (recommended script):

```powershell
cd "$REPO"
powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend.ps1
```

Or start manually:

```powershell
cd "$REPO\frontend"
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

Open:
- http://localhost:8503

## First Run Workflow

1. Start backend on port `8888`.
2. Start frontend on port `8503`.
3. In the UI sidebar, keep backend URL as `http://127.0.0.1:8888`.
4. Use one of:
   - `Voice Compile` (mic or upload audio)
   - `Transcript Parse` (text only)
5. Optionally `Compile -> Save Memory -> Generate YAML`.
6. Optionally `Run Up` / `Fetch Logs` / `Run Down` (requires Docker).

Generated project files are written under:
- `generated/<project_name>/`

## Microphone Checklist

If mic capture is empty or transcription fails:

1. Use `http://localhost:8503` (localhost is important for browser mic permissions).
2. In browser site permissions, set microphone to **Allow**.
3. Record flow:
   - Click `Start recording`
   - Speak for 5-10 seconds
   - Click `Stop recording`
   - Confirm audio preview appears
   - Click `Voice Compile`
4. Open `Audio payload debug` in the UI and check:
   - Non-zero `size_bytes`
   - `is_riff_wave: true` for mic WAV payload
5. If mic is invalid, use upload fallback (`Upload Audio`).

## Troubleshooting

### Wrong Python is being used

Always run using venv python explicitly:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

Check command resolution:

```powershell
(Get-Command python).Source
(Get-Command streamlit).Source
```

If PowerShell blocks script activation, run this in that terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Port already in use

If `8503` or `8888` is busy, choose a different port:

```powershell
uvicorn app.main:app --reload --port 8890
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8504
```

Then set the frontend backend URL to match.

### Speechmatics STT errors

Check:
- `SPEECHMATICS_API_KEY` is present in `backend\.env`
- Backend logs for upload metadata (`filename`, `content_type`, `size_bytes`, `has_riff_wave`)
- Audio payload is not empty

### FFmpeg not installed

Install FFmpeg and restart terminal/app.

## Useful API Endpoints

From backend Swagger (`/docs`) or directly:

- `POST /parse`
- `POST /voice/compile`
- `POST /generate`
- `GET /memory/{project_name}`
- `POST /memory/{project_name}`
- `DELETE /memory/{project_name}`
- `POST /update/preview/{project_name}`
- `POST /update/apply/{project_name}`
- `POST /run/up`
- `POST /run/down`
- `POST /run/logs`

## Project Structure

```text
voice-scaffold/
  backend/                  FastAPI app
  frontend/                 Streamlit app
  generated/                Generated project output
  memory/                   Persisted AST memory
  scripts/
    start_frontend.ps1      Portable frontend launcher
  templates/                Scaffold templates
  tests/
```

## Stop Services

- Backend: press `Ctrl + C` in backend terminal
- Frontend: press `Ctrl + C` in frontend terminal

## Notes

- Voice features require external network access for Speechmatics/OpenAI APIs.
