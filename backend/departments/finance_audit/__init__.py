from departments.base import DepartmentSpec
from departments.finance_audit.agents import DEPARTMENT_ID, on_task_received
from departments.finance_audit.aspects import ASPECTS

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Finance & Audit",
    description=(
        "Accounts-payable invoice review: extracts invoice fields, classifies "
        "the expense, runs a two-stage fraud check, verifies the result "
        "deterministically, and explains the outcome in plain language."
    ),
    accepted_task_types=["review_invoice"],
    memory_namespace="finance_audit",
    on_task_received=on_task_received,
    aspects=ASPECTS,
)

__all__ = ["SPEC"]
