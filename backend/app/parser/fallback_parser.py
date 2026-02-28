from __future__ import annotations

import re
from typing import Any, Dict, List


def fallback_parse(transcript: str) -> Dict[str, Any]:
    t = transcript.lower()

    if "fastapi" in t or "postgres" in t or "redis" in t or "api" in t:
        template = "api_microservice_stack"
        services = [
            {"name": "fastapi", "type": "api", "port": 8000},
            {"name": "postgres", "type": "database", "port": 5432},
            {"name": "redis", "type": "cache", "port": 6379},
        ]
        project_name = "api-microservice"
    else:
        template = "realtime_data_stack"
        services = [
            {"name": "kafka", "type": "broker", "port": 9092},
            {"name": "spark", "type": "stream_processor", "port": 4040},
            {"name": "duckdb", "type": "analytics_db", "port": 5432},
            {"name": "streamlit", "type": "dashboard", "port": 8501},
        ]
        project_name = "realtime-stack"

    # crude project name extraction
    m = re.search(r"project(?: name)?\s*[:=]\s*([a-z0-9\-_\s]+)", t)
    if m:
        project_name = m.group(1).strip().replace(" ", "-")[:40]

    return {"project_name": project_name, "template": template, "services": services}
