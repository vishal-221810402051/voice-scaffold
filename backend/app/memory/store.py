from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.architecture.models import InfraAST


def _repo_root() -> Path:
    # backend/app/memory -> backend/app -> backend -> repo root
    return Path(__file__).resolve().parents[3]


def _memory_dir(project_name: str) -> Path:
    root = _repo_root()
    base = (root / "memory").resolve()
    target = (base / project_name).resolve()

    # Hard block traversal outside memory/
    if not str(target).startswith(str(base)):
        raise ValueError("Invalid project path")

    target.mkdir(parents=True, exist_ok=True)
    return target


def load_ast(project_name: str) -> Optional[InfraAST]:
    d = _memory_dir(project_name)
    p = d / "ast.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return InfraAST(**data)


def save_ast(project_name: str, ast: InfraAST) -> Path:
    d = _memory_dir(project_name)
    p = d / "ast.json"
    p.write_text(json.dumps(ast.model_dump(), indent=2), encoding="utf-8", newline="\n")
    return p


def delete_ast(project_name: str) -> bool:
    d = _memory_dir(project_name)
    p = d / "ast.json"
    if p.exists():
        p.unlink()
        return True
    return False
