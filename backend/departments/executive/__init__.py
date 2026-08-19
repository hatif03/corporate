from departments.base import DepartmentSpec
from departments.executive.agents import DEPARTMENT_ID, on_task_received

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Office of the CEO",
    description=(
        "Cross-department digest: reads every department's current task and "
        "agent state and publishes a company-wide announcement to the "
        "shared board."
    ),
    accepted_task_types=["company_digest"],
    memory_namespace="executive",
    on_task_received=on_task_received,
)

__all__ = ["SPEC"]
