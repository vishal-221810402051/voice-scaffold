from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


INFRA_AST_SCHEMA = {
    "name": "InfraAST",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["project_name", "template", "services"],
        "properties": {
            "project_name": {"type": "string", "minLength": 3},
            "template": {"type": "string", "enum": ["realtime_data_stack", "api_microservice_stack"]},
            "services": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "type", "port"],
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    },
                },
            },
        },
    },
    "strict": True,
}


def extract_infra_ast_from_transcript(transcript: str) -> Dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in environment")

    prompt = (
        "Convert this architecture intent into an Infra AST JSON.\n"
        "Rules:\n"
        "- Only TWO templates: realtime_data_stack or api_microservice_stack\n"
        "- For realtime_data_stack include services: kafka, spark, duckdb, streamlit\n"
        "- For api_microservice_stack include services: fastapi, postgres, redis\n"
        "- Choose sensible default ports if not specified.\n"
        "Return ONLY valid JSON that matches the schema.\n\n"
        f"TRANSCRIPT:\n{transcript}\n"
    )

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "json_schema": INFRA_AST_SCHEMA,
            }
        },
    )

    # Responses API returns structured output in output_text for json_schema mode
    # We'll parse from the first output text block.
    out = resp.output_text
    # output_text is already JSON string; parse using stdlib
    import json
    return json.loads(out)
