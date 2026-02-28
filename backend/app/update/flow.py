from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.architecture.models import InfraAST
from app.diff_engine.diff import compute_ast_diff
from app.memory.store import load_ast, save_ast
from app.validation.validator import validate_schema_and_rules
from app.validation.errors import issues_to_response
from app.generator.scaffold import generate_project


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def preview_update(project_name: str, new_ast: InfraAST) -> Dict[str, Any]:
    old_ast = load_ast(project_name)
    if old_ast is None:
        # If no memory exists, treat as "new project"
        diff = {"ok": True, "summary": {"project_name_changed": False, "template_changed": False,
                                       "services_added": [s.name for s in new_ast.services],
                                       "services_removed": [], "ports_changed": [], "types_changed": []},
                "raw": {}}
    else:
        diff = compute_ast_diff(old_ast, new_ast)

    issues = validate_schema_and_rules(new_ast)
    validation = issues_to_response(issues)

    return {
        "ok": True,
        "old_ast": old_ast.model_dump() if old_ast else None,
        "new_ast": new_ast.model_dump(),
        "diff": diff,
        "validation": validation,
    }


def apply_update(project_name: str, new_ast: InfraAST) -> Dict[str, Any]:
    # Validate first
    issues = validate_schema_and_rules(new_ast)
    validation = issues_to_response(issues)
    if not validation["valid"]:
        return {"ok": False, "validation": validation}

    # Persist
    saved_path = save_ast(project_name, new_ast)

    # Regenerate deterministically
    repo_root = _repo_root()
    gen_result = generate_project(new_ast, repo_root=repo_root)

    return {
        "ok": True,
        "saved_path": str(saved_path),
        "generation": {
            "project_dir": gen_result.project_dir,
            "files_written": gen_result.files_written,
        },
        "validation": validation,
    }
