from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# Speechmatics official python SDK
# Repo: https://github.com/speechmatics/speechmatics-python-sdk
from speechmatics.batch_client import BatchClient


load_dotenv()


def transcribe_file_batch(audio_path: Path, language: str = "en") -> str:
    """
    Deterministic batch transcription using Speechmatics SDK.
    Returns plain transcript string.
    """
    api_key = os.getenv("SPEECHMATICS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing SPEECHMATICS_API_KEY in environment")

    # Batch transcription client
    # Minimal config, deterministic
    config = {
        "type": "transcription",
        "transcription_config": {
            "language": language,
            "diarization": "none",
        },
    }

    # Submit + wait for completion
    with BatchClient(api_key) as client:
        job_id = client.submit_job(
            audio=str(audio_path),
            transcription_config=config,
        )
        result = client.wait_for_completion(job_id, transcription_format="txt")

    # SDK returns transcript content in the chosen format
    # Normalize to string
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="ignore")
    return str(result).strip()
