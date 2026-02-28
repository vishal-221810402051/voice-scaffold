from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class TemplateType(str, Enum):
    realtime_data_stack = "realtime_data_stack"
    api_microservice_stack = "api_microservice_stack"


class Service(BaseModel):
    name: str
    type: str
    port: int = Field(..., ge=1024, le=65535)


class InfraAST(BaseModel):
    project_name: str = Field(..., min_length=3)
    template: TemplateType
    services: List[Service]
