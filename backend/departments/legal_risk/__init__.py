from departments.base import DepartmentSpec
from departments.legal_risk.agents import DEPARTMENT_ID, on_task_received

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Legal & Risk",
    description=(
        "Live decision-conflict detection: checks a new statement against "
        "known legal constraints, prior decisions, capacity, dependencies, "
        "and customer promises — five parallel judge lenses, each finding "
        "deterministically grounded against the source context before it's "
        "ever surfaced."
    ),
    accepted_task_types=["check_decision_conflict"],
    memory_namespace="legal_risk",
    on_task_received=on_task_received,
)

__all__ = ["SPEC"]
