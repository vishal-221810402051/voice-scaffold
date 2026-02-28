from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.architecture.models import InfraAST, TemplateType
from app.generator.template_a import generate_template_a


@dataclass(frozen=True)
class GenerationResult:
    project_dir: str
    files_written: List[str]


def _jinja_env(templates_root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_root)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def generate_project(ast: InfraAST, repo_root: Path) -> GenerationResult:
    """
    Deterministically generate scaffold into:
      <repo_root>/generated/<project_name>/

    No execution. No diff. No side effects outside generated/.
    """
    out_dir = repo_root / "generated" / ast.project_name
    out_dir.mkdir(parents=True, exist_ok=True)

    templates_root = repo_root / "templates"
    env = _jinja_env(templates_root)

    files_written: List[str] = []

    if ast.template == TemplateType.realtime_data_stack:
        files_written.extend(generate_template_a(ast, env, out_dir))
    else:
        raise ValueError(f"Template not supported in Phase 3: {ast.template.value}")

    return GenerationResult(project_dir=str(out_dir), files_written=sorted(files_written))
