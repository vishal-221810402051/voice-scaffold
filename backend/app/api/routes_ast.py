import json
from fastapi import APIRouter, HTTPException
from jsonschema import validate, ValidationError

from app.architecture.models import InfraAST

router = APIRouter()


def load_schema():
    with open("app/architecture/schema.json", "r", encoding="utf-8-sig") as f:
        return json.load(f)


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

