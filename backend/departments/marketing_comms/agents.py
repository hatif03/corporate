"""Marketing & Comms: brief intake -> copy draft -> brand-voice verify
(deterministic, shared/verification.py) -> scheduling suggestion. If the
draft fails brand-voice verification, it comes back needing a human rewrite
instead of a wasted scheduling suggestion for copy that won't ship as-is."""

from __future__ import annotations

from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.marketing_comms.aspects import ASPECTS
from shared.custom_skills import with_custom_guidance
from shared.verification import vote_aspects

DEPARTMENT_ID = "marketing_comms"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    return build_tiered_stage_agents(
        name, instruction=_load_prompt(prompt_file), description=f"Marketing & Comms pipeline stage: {name}"
    )


brief_agents = _build_stage_agents("marketing_brief_intake", "brief_intake")
copy_agents = _build_stage_agents("marketing_copy_drafter", "copy_drafter")
scheduler_agents = _build_stage_agents("marketing_scheduler", "scheduler")

_session_service = FirestoreSessionService()


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    brief = await run_agent_turn(
        brief_agents[tier], _session_service, org_id, DEPARTMENT_ID,
        with_custom_guidance(org_id, DEPARTMENT_ID, task.description), attachment=task.attachment
    )
    copy = await run_agent_turn(copy_agents[tier], _session_service, org_id, DEPARTMENT_ID, brief)

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

    schedule_suggestion = await run_agent_turn(scheduler_agents[tier], _session_service, org_id, DEPARTMENT_ID, copy)

    return TaskResult(
        success=True,
        summary=f"{copy}\n\nSuggested timing: {schedule_suggestion}",
        data={"copy": copy, "brand_voice_passed": True, "schedule_suggestion": schedule_suggestion},
        needs_human=False,
    )
