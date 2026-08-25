from departments.base import DepartmentSpec
from departments.sales_crm.agents import DEPARTMENT_ID, on_task_received, sales_pipeline_by_tier

SPEC = DepartmentSpec(
    department_id=DEPARTMENT_ID,
    display_name="Sales & CRM",
    description=(
        "Lead qualification, deal strategy (with a hard-capped pricing "
        "guardrail), and outreach drafting. Exposed externally via A2A — "
        "see ADR-0004 and app/main.py."
    ),
    accepted_task_types=["qualify_lead"],
    memory_namespace="sales_crm",
    on_task_received=on_task_received,
    # External A2A callers never go through create_task's model_tier
    # (ADR-0013) — always the flash tier for them.
    root_agent=sales_pipeline_by_tier["flash"],
    a2a_exposed=True,
)

__all__ = ["SPEC"]
