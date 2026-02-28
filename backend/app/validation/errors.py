from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# Stable error codes for demo determinism
PORT_COLLISION = "PORT_COLLISION"
PORT_RESERVED = "PORT_RESERVED"
MISSING_REQUIRED_SERVICE = "MISSING_REQUIRED_SERVICE"
UNEXPECTED_SERVICE_FOR_TEMPLATE = "UNEXPECTED_SERVICE_FOR_TEMPLATE"
INVALID_SERVICE_TYPE = "INVALID_SERVICE_TYPE"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "path": self.path}


def issues_to_response(issues: List[ValidationIssue]) -> Dict[str, Any]:
    return {"valid": len(issues) == 0, "errors": [i.to_dict() for i in issues]}
