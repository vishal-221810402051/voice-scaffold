from __future__ import annotations

from typing import Dict, List, Set, Tuple

from app.architecture.models import InfraAST, TemplateType, Service
from app.validation.errors import (
    ValidationIssue,
    PORT_COLLISION,
    PORT_RESERVED,
    MISSING_REQUIRED_SERVICE,
    UNEXPECTED_SERVICE_FOR_TEMPLATE,
    INVALID_SERVICE_TYPE,
)

# Deterministic required services per template
REQUIRED_SERVICES: Dict[str, Set[str]] = {
    TemplateType.realtime_data_stack.value: {"kafka", "spark", "duckdb", "streamlit"},
    TemplateType.api_microservice_stack.value: {"fastapi", "postgres", "redis"},
}

# Optional but demo-stabilizing expected types per service name
EXPECTED_TYPES: Dict[str, Dict[str, str]] = {
    TemplateType.realtime_data_stack.value: {
        "kafka": "broker",
        "spark": "stream_processor",
        "duckdb": "analytics_db",
        "streamlit": "dashboard",
    },
    TemplateType.api_microservice_stack.value: {
        "fastapi": "api",
        "postgres": "database",
        "redis": "cache",
    },
}

# Small deterministic reserved ports list (avoid classic privileged + common conflicts)
# Note: We already enforce >=1024 in schema; this focuses on demo-safe avoidance.
RESERVED_PORTS: Set[int] = {3000, 3306, 5432, 6379, 8000, 8501, 9092, 27017}


def rule_port_collisions(ast: InfraAST) -> List[ValidationIssue]:
    port_to_services: Dict[int, List[str]] = {}
    for svc in ast.services:
        port_to_services.setdefault(svc.port, []).append(svc.name)

    issues: List[ValidationIssue] = []
    for port, names in sorted(port_to_services.items(), key=lambda x: x[0]):
        if len(names) > 1:
            issues.append(
                ValidationIssue(
                    code=PORT_COLLISION,
                    message=f"Port {port} is used by multiple services: {', '.join(sorted(names))}",
                    path="$.services[*].port",
                )
            )
    return issues


def rule_reserved_ports(ast: InfraAST) -> List[ValidationIssue]:
    # Reserved ports are allowed only if they are part of the "known stack" ports.
    # For hackathon determinism we still allow them, but we flag if unknown services use them.
    # This prevents "random service on 5432" type mistakes.
    known_ports = {s.port for s in ast.services}
    issues: List[ValidationIssue] = []

    # If any service uses a port in RESERVED_PORTS, it must be one of our recognized service names.
    recognized = REQUIRED_SERVICES.get(ast.template.value, set())
    for svc in sorted(ast.services, key=lambda s: (s.port, s.name)):
        if svc.port in RESERVED_PORTS and svc.name not in recognized:
            issues.append(
                ValidationIssue(
                    code=PORT_RESERVED,
                    message=f"Service '{svc.name}' uses reserved/demo-sensitive port {svc.port}",
                    path="$.services[*].port",
                )
            )
    return issues


def rule_required_services(ast: InfraAST) -> List[ValidationIssue]:
    required = REQUIRED_SERVICES.get(ast.template.value, set())
    present = {s.name for s in ast.services}

    missing = sorted(list(required - present))
    issues: List[ValidationIssue] = []
    for name in missing:
        issues.append(
            ValidationIssue(
                code=MISSING_REQUIRED_SERVICE,
                message=f"Template '{ast.template.value}' requires service '{name}'",
                path="$.services[*].name",
            )
        )
    return issues


def rule_unexpected_services(ast: InfraAST) -> List[ValidationIssue]:
    required = REQUIRED_SERVICES.get(ast.template.value, set())
    present = {s.name for s in ast.services}

    unexpected = sorted(list(present - required))
    issues: List[ValidationIssue] = []
    for name in unexpected:
        issues.append(
            ValidationIssue(
                code=UNEXPECTED_SERVICE_FOR_TEMPLATE,
                message=f"Service '{name}' is not allowed for template '{ast.template.value}'",
                path="$.services[*].name",
            )
        )
    return issues


def rule_expected_types(ast: InfraAST) -> List[ValidationIssue]:
    expected = EXPECTED_TYPES.get(ast.template.value, {})
    issues: List[ValidationIssue] = []

    # Only validate type if service name is recognized for the template
    for svc in sorted(ast.services, key=lambda s: s.name):
        if svc.name in expected:
            exp_type = expected[svc.name]
            if svc.type != exp_type:
                issues.append(
                    ValidationIssue(
                        code=INVALID_SERVICE_TYPE,
                        message=f"Service '{svc.name}' must have type '{exp_type}' (got '{svc.type}')",
                        path="$.services[*].type",
                    )
                )
    return issues


def run_all_rules(ast: InfraAST) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    # Order matters for deterministic outputs
    issues.extend(rule_required_services(ast))
    issues.extend(rule_unexpected_services(ast))
    issues.extend(rule_port_collisions(ast))
    issues.extend(rule_expected_types(ast))
    issues.extend(rule_reserved_ports(ast))
    return issues
