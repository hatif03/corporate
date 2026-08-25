"""Sales & CRM: lead qualification -> deal strategy -> outreach draft, built
as a real ADK SequentialAgent (unlike Finance/Engineering/Legal's plain-Python
orchestration) because this department needs a genuine root_agent to expose
via A2A (ADR-0004). See ADR-0009 for the SequentialAgent-deprecation tradeoff
this required.
"""

from __future__ import annotations

from pathlib import Path

from google.adk.agents.sequential_agent import SequentialAgent

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.sales_crm.tools import pricing_guardrail

DEPARTMENT_ID = "sales_crm"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


_lead_qualifier_agents = build_tiered_stage_agents(
    "sales_lead_qualifier", instruction=_load_prompt("lead_qualifier"),
    description="Sales & CRM pipeline stage: lead qualification",
)

_deal_strategist_agents = build_tiered_stage_agents(
    "sales_deal_strategist", instruction=_load_prompt("deal_strategist"),
    description="Sales & CRM pipeline stage: deal strategy (pricing_guardrail-enforced)",
    extra_tools=[pricing_guardrail],
)

_outreach_drafter_agents = build_tiered_stage_agents(
    "sales_outreach_drafter", instruction=_load_prompt("outreach_drafter"),
    description="Sales & CRM pipeline stage: outreach draft",
)

# One full SequentialAgent pipeline per tier — sub_agents can't be swapped
# per-call on a shared singleton (see ADR-0013 / app/adk_agents/factory.py's
# build_tiered_stage_agents docstring), so this department builds two whole
# pipelines instead of one. sales_pipeline_by_tier["flash"] is also this
# department's root_agent (for A2A exposure, see departments/sales_crm/__init__.py
# and app/main.py) — external A2A callers never go through create_task's
# model_tier, so they always get the safe/cheap default.
sales_pipeline_by_tier = {
    tier: SequentialAgent(
        name=f"sales_crm_pipeline_{tier}",
        sub_agents=[_lead_qualifier_agents[tier], _deal_strategist_agents[tier], _outreach_drafter_agents[tier]],
    )
    for tier in ("flash", "pro")
}

_session_service = FirestoreSessionService()


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    outreach_draft = await run_agent_turn(
        sales_pipeline_by_tier[tier], _session_service, org_id, DEPARTMENT_ID, task.description,
        attachment=task.attachment,
    )
    return TaskResult(success=True, summary=outreach_draft, data={"draft": outreach_draft}, needs_human=False)
