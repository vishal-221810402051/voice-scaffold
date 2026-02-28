from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.architecture.models import InfraAST, TemplateType
from app.validation.validator import validate_schema_and_rules
from app.validation.errors import issues_to_response
from app.generator.scaffold import generate_project

router = APIRouter()


@router.post("/generate")
def generate(ast: InfraAST):
    # Enforce schema + rules before generation (deterministic)
    issues = validate_schema_and_rules(ast)
    resp = issues_to_response(issues)
    if not resp["valid"]:
        raise HTTPException(status_code=400, detail=resp)

    # Phase 3 supports Template A only
    if ast.template != TemplateType.realtime_data_stack:
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "errors": [
                    {
                        "code": "TEMPLATE_NOT_AVAILABLE",
                        "message": "Phase 3 supports only 'realtime_data_stack' (Template A).",
                        "path": "$.template",
                    }
                ],
            },
        )

    repo_root = Path(__file__).resolve().parents[3]  # backend/app/api -> backend -> repo root
    result = generate_project(ast, repo_root=repo_root)
    return {
        "ok": True,
        "project_dir": result.project_dir,
        "files_written": result.files_written,
    }
