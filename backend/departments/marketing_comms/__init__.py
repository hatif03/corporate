from departments.base import DepartmentSpec
from departments.marketing_comms.agents import DEPARTMENT_ID, on_task_received
from departments.marketing_comms.aspects import ASPECTS

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Marketing & Comms",
    description=(
        "Turns a content brief into drafted copy, checks it against "
        "deterministic brand-voice rules before it can ship, and suggests "
        "publish timing for anything that passes."
    ),
    accepted_task_types=["marketing_request"],
    memory_namespace="marketing_comms",
    on_task_received=on_task_received,
    aspects=ASPECTS,
)

__all__ = ["SPEC"]
