import json
from fastapi import APIRouter, HTTPException
from jsonschema import validate, ValidationError

from app.architecture.models import InfraAST
from app.validation.validator import load_schema, validate_schema_and_rules
from app.validation.errors import issues_to_response

router = APIRouter()


@router.get("/ast/schema")
def get_schema():
    return load_schema()


@router.post("/ast/validate")
def validate_ast(ast: InfraAST):
    schema = load_schema()
    try:
        validate(instance=ast.model_dump(), schema=schema)
        return {"valid": True}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ast/validate_rules")
def validate_ast_rules(ast: InfraAST):
    issues = validate_schema_and_rules(ast)
    response = issues_to_response(issues)
    if not response["valid"]:
        raise HTTPException(status_code=400, detail=response)
    return response
