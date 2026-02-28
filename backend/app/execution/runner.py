from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional


def _repo_root() -> Path:
    # backend/app/execution -> backend/app -> backend -> repo root
    return Path(__file__).resolve().parents[3]


def _project_dir(project_name: str) -> Path:
    root = _repo_root()
    base = (root / "generated").resolve()
    target = (base / project_name).resolve()

    # Hard block traversal outside generated/
    if not str(target).startswith(str(base)):
        raise ValueError("Invalid project path")

    if not target.exists():
        raise FileNotFoundError(f"Project not found: generated/{project_name}")

    compose = target / "docker-compose.yml"
    if not compose.exists():
        raise FileNotFoundError("docker-compose.yml not found in project")

    return target


def _run(cmd: list[str], cwd: Path, timeout: int = 180) -> Dict[str, str]:
    """
    Deterministic subprocess runner.
    Returns stdout/stderr for API visibility.
    """
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return {
        "cmd": " ".join(cmd),
        "returncode": str(proc.returncode),
        "stdout": (proc.stdout or "")[-8000:],  # cap for API stability
        "stderr": (proc.stderr or "")[-8000:],
    }


def compose_up(project_name: str) -> Dict[str, str]:
    proj = _project_dir(project_name)
    return _run(["docker", "compose", "up", "-d"], cwd=proj, timeout=300)


def compose_down(project_name: str) -> Dict[str, str]:
    proj = _project_dir(project_name)
    return _run(["docker", "compose", "down"], cwd=proj, timeout=300)


def compose_logs(project_name: str, tail: int = 200) -> Dict[str, str]:
    proj = _project_dir(project_name)
    return _run(["docker", "compose", "logs", "--no-color", f"--tail={tail}"], cwd=proj, timeout=60)
