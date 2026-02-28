from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.architecture.models import InfraAST
from app.validation.validator import validate_schema_and_rules
from app.validation.errors import issues_to_response
from app.voice.speechmatics_client import transcribe_file_batch
from app.parser.openai_extractor import extract_infra_ast_from_transcript
from app.parser.fallback_parser import fallback_parse

router = APIRouter()


class ParseRequest(BaseModel):
    transcript: str


@router.post("/parse")
def parse_transcript(req: ParseRequest):
    # Try OpenAI structured extraction first; fallback if it fails
    try:
        ast_dict = extract_infra_ast_from_transcript(req.transcript)
    except Exception:
        ast_dict = fallback_parse(req.transcript)

    # Validate into Pydantic first
    try:
        ast = InfraAST(**ast_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "AST_MODEL_ERROR", "message": str(e)})

    issues = validate_schema_and_rules(ast)
    resp = issues_to_response(issues)

    return {
        "ok": True,
        "ast": ast.model_dump(),
        "validation": resp,
    }


@router.post("/voice/compile")
def voice_compile(audio: UploadFile = File(...), language: str = "en"):
    # Save upload to temp file
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio.file.read())
        tmp_path = Path(tmp.name)

    try:
        transcript = transcribe_file_batch(tmp_path, language=language)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "STT_FAILED", "message": str(e)})
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    # Parse transcript to AST
    parsed = parse_transcript(ParseRequest(transcript=transcript))
    parsed["transcript"] = transcript
    return parsed
