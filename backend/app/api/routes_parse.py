from __future__ import annotations

import logging
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
logger = logging.getLogger(__name__)


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
    payload = audio.file.read()
    payload_size = len(payload)
    header = payload[:12] if payload else b""
    has_riff_wave = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"

    logger.info(
        "voice_compile upload filename=%s content_type=%s language=%s size_bytes=%d has_riff_wave=%s header_hex=%s",
        audio.filename,
        audio.content_type,
        language,
        payload_size,
        has_riff_wave,
        header.hex(),
    )

    if payload_size == 0:
        raise HTTPException(status_code=400, detail={"error": "EMPTY_AUDIO", "message": "Uploaded audio payload is empty."})

    # Save upload to temp file
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(payload)
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
