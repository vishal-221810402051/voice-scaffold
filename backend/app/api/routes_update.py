from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.architecture.models import InfraAST
from app.parser.openai_extractor import extract_infra_ast_from_transcript
from app.parser.fallback_parser import fallback_parse
from app.voice.speechmatics_client import transcribe_file_batch
from app.update.flow import preview_update, apply_update

router = APIRouter()


class TranscriptRequest(BaseModel):
    transcript: str = Field(..., min_length=3)


class ApplyAstRequest(BaseModel):
    new_ast: InfraAST | None = None
    transcript: str | None = Field(default=None, min_length=3)


def _transcript_to_ast(transcript: str) -> InfraAST:
    try:
        ast_dict = extract_infra_ast_from_transcript(transcript)
    except Exception:
        ast_dict = fallback_parse(transcript)

    return InfraAST(**ast_dict)


@router.post("/update/preview/{project_name}")
def update_preview(project_name: str, req: TranscriptRequest):
    try:
        new_ast = _transcript_to_ast(req.transcript)
        new_ast = new_ast.model_copy(update={"project_name": project_name})
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "PARSE_FAILED", "message": str(e)})

    return preview_update(project_name, new_ast)


@router.post("/update/apply/{project_name}")
def update_apply(project_name: str, req: ApplyAstRequest):
    if req.new_ast is not None:
        new_ast = req.new_ast
    elif req.transcript is not None:
        try:
            new_ast = _transcript_to_ast(req.transcript)
            new_ast = new_ast.model_copy(update={"project_name": project_name})
        except Exception as e:
            raise HTTPException(status_code=400, detail={"error": "PARSE_FAILED", "message": str(e)})
    else:
        raise HTTPException(status_code=400, detail={"error": "MISSING_UPDATE", "message": "Provide new_ast or transcript"})

    result = apply_update(project_name, new_ast)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/voice/update/preview/{project_name}")
def voice_update_preview(project_name: str, audio: UploadFile = File(...), language: str = "en"):
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio.file.read())
        tmp_path = Path(tmp.name)

    try:
        transcript = transcribe_file_batch(tmp_path, language=language)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    new_ast = _transcript_to_ast(transcript)
    new_ast = new_ast.model_copy(update={"project_name": project_name})
    out = preview_update(project_name, new_ast)
    out["transcript"] = transcript
    return out


@router.post("/voice/update/apply/{project_name}")
def voice_update_apply(project_name: str, audio: UploadFile = File(...), language: str = "en"):
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio.file.read())
        tmp_path = Path(tmp.name)

    try:
        transcript = transcribe_file_batch(tmp_path, language=language)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    new_ast = _transcript_to_ast(transcript)
    new_ast = new_ast.model_copy(update={"project_name": project_name})
    result = apply_update(project_name, new_ast)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result)
    result["transcript"] = transcript
    return result
