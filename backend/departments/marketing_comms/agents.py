"""Marketing & Comms: brief intake -> copy draft -> brand-voice verify
(deterministic, shared/verification.py) -> scheduling suggestion. If the
draft fails brand-voice verification, it comes back needing a human rewrite
instead of a wasted scheduling suggestion for copy that won't ship as-is."""

from __future__ import annotations

from pathlib import Path

from google.adk.agents.llm_agent import LlmAgent

from app.adk_agents.factory import department_callbacks, department_tools
from app.adk_agents.runtime import run_agent_turn
from app.config import settings
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.marketing_comms.aspects import ASPECTS
from shared.verification import vote_aspects

DEPARTMENT_ID = "marketing_comms"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agent(name: str, prompt_file: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=settings.corporate_gemini_model,
        instruction=_load_prompt(prompt_file),
        description=f"Marketing & Comms pipeline stage: {name}",
        tools=department_tools(),
        **department_callbacks(),
    )


brief_agent = _build_stage_agent("marketing_brief_intake", "brief_intake")
copy_agent = _build_stage_agent("marketing_copy_drafter", "copy_drafter")
scheduler_agent = _build_stage_agent("marketing_scheduler", "scheduler")

_session_service = FirestoreSessionService()


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    brief = await run_agent_turn(brief_agent, _session_service, org_id, DEPARTMENT_ID, task.description)
    copy = await run_agent_turn(copy_agent, _session_service, org_id, DEPARTMENT_ID, brief)

    verified = await vote_aspects({"copy": copy}, ASPECTS)

    if not verified.verified:
        failed_reasons = "; ".join(v.reason for v in verified.votes if not v.passed)
        return TaskResult(
            success=False,
            summary=f"Draft copy failed brand-voice review: {failed_reasons}",
            data={"copy": copy, "brand_voice_passed": False},
            needs_human=True,
            human_question=f"Marketing copy needs a rewrite — {failed_reasons}",
        )

    schedule_suggestion = await run_agent_turn(scheduler_agent, _session_service, org_id, DEPARTMENT_ID, copy)

    return TaskResult(
        success=True,
        summary=f"{copy}\n\nSuggested timing: {schedule_suggestion}",
        data={"copy": copy, "brand_voice_passed": True, "schedule_suggestion": schedule_suggestion},
        needs_human=False,
    )
