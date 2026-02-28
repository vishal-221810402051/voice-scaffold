from __future__ import annotations

import json
from jsonschema import validate, ValidationError

from app.architecture.models import InfraAST
from app.validation.rules import run_all_rules
from app.validation.errors import ValidationIssue


def load_schema() -> dict:
    # BOM-safe read for Windows/PowerShell created files
    with open("app/architecture/schema.json", "r", encoding="utf-8-sig") as f:
        return json.load(f)


def validate_schema_only(ast: InfraAST) -> list[ValidationIssue]:
    schema = load_schema()
    try:
        validate(instance=ast.model_dump(), schema=schema)
        return []
    except ValidationError as e:
        return [ValidationIssue(code="SCHEMA_VALIDATION_ERROR", message=str(e), path="$")]


def validate_schema_and_rules(ast: InfraAST) -> list[ValidationIssue]:
    issues = validate_schema_only(ast)
    if issues:
        return issues
    issues.extend(run_all_rules(ast))
    return issues
