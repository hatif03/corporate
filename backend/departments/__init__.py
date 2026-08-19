"""Auto-discovers every department's SPEC at import time.

To add a department: create backend/departments/<dept_id>/__init__.py
exporting `SPEC = DepartmentSpec(...)` and it is picked up automatically —
no registration step anywhere else. See the `new-department` Claude Code
skill for scaffolding a new one.
"""

from __future__ import annotations

import importlib
import pkgutil

from departments.base import DepartmentSpec

_registry: dict[str, DepartmentSpec] = {}


def _discover() -> dict[str, DepartmentSpec]:
    if _registry:
        return _registry
    package = importlib.import_module(__name__)
    for _finder, name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg or name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{name}")
        spec = getattr(module, "SPEC", None)
        if spec is not None:
            _registry[spec.department_id] = spec
    return _registry


def get_department(department_id: str) -> DepartmentSpec | None:
    return _discover().get(department_id)


def list_departments() -> list[DepartmentSpec]:
    return list(_discover().values())
