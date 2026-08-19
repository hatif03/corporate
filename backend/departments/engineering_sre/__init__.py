from departments.base import DepartmentSpec
from departments.engineering_sre.agents import DEPARTMENT_ID, on_task_received

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Engineering & SRE",
    description=(
        "Incident response: triages an incident report, assesses cascade "
        "risk to other systems, and drafts a postmortem — redacting PII "
        "before any of it reaches Gemini."
    ),
    accepted_task_types=["handle_incident"],
    memory_namespace="engineering_sre",
    on_task_received=on_task_received,
)

__all__ = ["SPEC"]
