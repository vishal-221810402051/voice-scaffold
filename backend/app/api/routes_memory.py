from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from app.architecture.models import InfraAST
from app.memory.store import load_ast, save_ast, delete_ast
from app.validation.validator import validate_schema_and_rules
from app.validation.errors import issues_to_response

router = APIRouter()


class SaveRequest(BaseModel):
    ast: InfraAST


@router.get("/memory/{project_name}")
def get_memory(project_name: str = Path(..., min_length=3)):
    try:
        ast = load_ast(project_name)
        if ast is None:
            raise HTTPException(status_code=404, detail="No stored AST for this project")
        return {"ok": True, "ast": ast.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/memory/{project_name}")
def put_memory(project_name: str = Path(..., min_length=3), req: SaveRequest = None):
    if req is None:
        raise HTTPException(status_code=400, detail="Missing request body")

    issues = validate_schema_and_rules(req.ast)
    resp = issues_to_response(issues)
    if not resp["valid"]:
        raise HTTPException(status_code=400, detail=resp)

    try:
        path = save_ast(project_name, req.ast)
        return {"ok": True, "path": str(path)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/memory/{project_name}")
def reset_memory(project_name: str = Path(..., min_length=3)):
    try:
        deleted = delete_ast(project_name)
        return {"ok": True, "deleted": deleted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
