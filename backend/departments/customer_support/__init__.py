from departments.base import DepartmentSpec
from departments.customer_support.agents import DEPARTMENT_ID, on_task_received

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Customer Support",
    description=(
        "Classifies a support ticket's intent and urgency, drafts a "
        "knowledge-base-grounded reply, and escalates to a human whenever "
        "the reply's cited evidence can't be verbatim-confirmed or the "
        "ticket is high-urgency."
    ),
    accepted_task_types=["support_ticket"],
    memory_namespace="customer_support",
    on_task_received=on_task_received,
)

__all__ = ["SPEC"]
