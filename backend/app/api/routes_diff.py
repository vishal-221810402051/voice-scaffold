from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.architecture.models import InfraAST
from app.diff_engine.diff import compute_ast_diff

router = APIRouter()


class DiffRequest(BaseModel):
    old: InfraAST
    new: InfraAST


@router.post("/diff")
def diff_ast(req: DiffRequest):
    return compute_ast_diff(req.old, req.new)
