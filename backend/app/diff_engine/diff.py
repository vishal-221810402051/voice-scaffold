from __future__ import annotations

from typing import Any, Dict, List, Tuple
from deepdiff import DeepDiff

from app.architecture.models import InfraAST


def _services_index(ast: InfraAST) -> Dict[str, Dict[str, Any]]:
    return {s.name: {"type": s.type, "port": s.port} for s in ast.services}


def compute_ast_diff(old: InfraAST, new: InfraAST) -> Dict[str, Any]:
    # Deterministic raw diff
    raw = DeepDiff(
        old.model_dump(),
        new.model_dump(),
        ignore_order=True,
        verbose_level=2,
    ).to_dict()

    old_s = _services_index(old)
    new_s = _services_index(new)

    old_names = set(old_s.keys())
    new_names = set(new_s.keys())

    added = sorted(list(new_names - old_names))
    removed = sorted(list(old_names - new_names))

    ports_changed: List[Dict[str, Any]] = []
    types_changed: List[Dict[str, Any]] = []

    for name in sorted(list(old_names & new_names)):
        if old_s[name]["port"] != new_s[name]["port"]:
            ports_changed.append(
                {"service": name, "from": old_s[name]["port"], "to": new_s[name]["port"]}
            )
        if old_s[name]["type"] != new_s[name]["type"]:
            types_changed.append(
                {"service": name, "from": old_s[name]["type"], "to": new_s[name]["type"]}
            )

    summary = {
        "project_name_changed": old.project_name != new.project_name,
        "template_changed": old.template != new.template,
        "services_added": added,
        "services_removed": removed,
        "ports_changed": ports_changed,
        "types_changed": types_changed,
    }

    return {"ok": True, "summary": summary, "raw": raw}
