$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $repoRoot "frontend")
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
