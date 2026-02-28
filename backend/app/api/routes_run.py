from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.execution.runner import compose_up, compose_down, compose_logs

router = APIRouter()


class RunRequest(BaseModel):
    project_name: str = Field(..., min_length=3)


class LogsRequest(BaseModel):
    project_name: str = Field(..., min_length=3)
    tail: int = Field(200, ge=10, le=2000)


@router.post("/run/up")
def run_up(req: RunRequest):
    try:
        result = compose_up(req.project_name)
        if result["returncode"] != "0":
            raise HTTPException(status_code=400, detail=result)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run/down")
def run_down(req: RunRequest):
    try:
        result = compose_down(req.project_name)
        if result["returncode"] != "0":
            raise HTTPException(status_code=400, detail=result)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run/logs")
def run_logs(req: LogsRequest):
    try:
        result = compose_logs(req.project_name, tail=req.tail)
        if result["returncode"] != "0":
            raise HTTPException(status_code=400, detail=result)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
