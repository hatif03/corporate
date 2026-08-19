"""Sales & CRM: lead qualification -> deal strategy -> outreach draft, built
as a real ADK SequentialAgent (unlike Finance/Engineering/Legal's plain-Python
orchestration) because this department needs a genuine root_agent to expose
via A2A (ADR-0004). See ADR-0009 for the SequentialAgent-deprecation tradeoff
this required.
"""

from __future__ import annotations

from pathlib import Path

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

from app.adk_agents.factory import department_callbacks, department_tools
from app.adk_agents.runtime import run_agent_turn
from app.config import settings
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.sales_crm.tools import pricing_guardrail

DEPARTMENT_ID = "sales_crm"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


lead_qualifier_agent = LlmAgent(
    name="sales_lead_qualifier",
    model=settings.corporate_gemini_model,
    instruction=_load_prompt("lead_qualifier"),
    description="Sales & CRM pipeline stage: lead qualification",
    tools=department_tools(),
    **department_callbacks(),
)

deal_strategist_agent = LlmAgent(
    name="sales_deal_strategist",
    model=settings.corporate_gemini_model,
    instruction=_load_prompt("deal_strategist"),
    description="Sales & CRM pipeline stage: deal strategy (pricing_guardrail-enforced)",
    tools=department_tools(extra_tools=[pricing_guardrail]),
    **department_callbacks(),
)

outreach_drafter_agent = LlmAgent(
    name="sales_outreach_drafter",
    model=settings.corporate_gemini_model,
    instruction=_load_prompt("outreach_drafter"),
    description="Sales & CRM pipeline stage: outreach draft",
    tools=department_tools(),
    **department_callbacks(),
)

# This IS the department's directly-invokable ADK agent tree — used both as
# root_agent (for A2A exposure, see app/main.py) and as what
# on_task_received actually runs internally, unlike the other departments.
sales_pipeline = SequentialAgent(
    name="sales_crm_pipeline",
    sub_agents=[lead_qualifier_agent, deal_strategist_agent, outreach_drafter_agent],
)

_session_service = FirestoreSessionService()


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    outreach_draft = await run_agent_turn(
        sales_pipeline, _session_service, org_id, DEPARTMENT_ID, task.description
    )
    return TaskResult(success=True, summary=outreach_draft, data={"draft": outreach_draft}, needs_human=False)
