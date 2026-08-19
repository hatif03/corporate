from departments.base import DepartmentSpec
from departments.hr_people_ops.agents import DEPARTMENT_ID, on_task_received

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="HR & People Ops",
    description=(
        "Classifies employee requests (onboarding, leave, policy questions) "
        "and answers against the company handbook. Leave requests always "
        "come back needing human HR approval."
    ),
    accepted_task_types=["hr_request"],
    memory_namespace="hr_people_ops",
    on_task_received=on_task_received,
)

__all__ = ["SPEC"]
