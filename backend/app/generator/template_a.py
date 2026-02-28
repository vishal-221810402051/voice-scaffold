from __future__ import annotations

from pathlib import Path
from typing import List

from jinja2 import Environment

from app.architecture.models import InfraAST


def _service_port(ast: InfraAST, name: str, default: int) -> int:
    for s in ast.services:
        if s.name == name:
            return s.port
    return default


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def generate_template_a(ast: InfraAST, env: Environment, out_dir: Path) -> List[str]:
    """
    Template A: Kafka + Spark Structured Streaming (Py) + DuckDB + Streamlit
    Deterministic file list and content.
    """
    # Map ports from AST (validated in Phase 2)
    ports = {
        "kafka": _service_port(ast, "kafka", 9092),
        "spark_ui": _service_port(ast, "spark", 4040),
        "duckdb": _service_port(ast, "duckdb", 5432),   # used only as a convention in README; DuckDB is embedded
        "streamlit": _service_port(ast, "streamlit", 8501),
    }

    context = {
        "project_name": ast.project_name,
        "ports": ports,
    }

    template_dir = "template_a"

    files = [
        ("docker-compose.yml", f"{template_dir}/docker-compose.yml.j2"),
        ("README.md", f"{template_dir}/README.md.j2"),
        ("src/api_producer.py", f"{template_dir}/api_producer.py.j2"),
        ("src/streaming_app.py", f"{template_dir}/streaming_app.py.j2"),
        ("dashboard/app.py", f"{template_dir}/dashboard_app.py.j2"),
        ("requirements.txt", f"{template_dir}/requirements.txt.j2"),
        ("scripts/run_producer.ps1", f"{template_dir}/run_producer.ps1.j2"),
        ("scripts/run_dashboard.ps1", f"{template_dir}/run_dashboard.ps1.j2"),
    ]

    written: List[str] = []

    for rel_out, tpl in files:
        rendered = env.get_template(tpl).render(**context)
        out_path = out_dir / rel_out
        _write_text(out_path, rendered)
        written.append(str(out_path))

    return written
