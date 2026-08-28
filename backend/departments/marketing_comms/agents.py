"""Marketing & Comms: brief intake -> copy draft -> brand-voice verify
(deterministic, shared/verification.py) -> scheduling suggestion. If the
draft fails brand-voice verification, it comes back needing a human rewrite
instead of a wasted scheduling suggestion for copy that won't ship as-is."""

from __future__ import annotations

from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services import store
from app.services.session_service import FirestoreSessionService
from app.services.veo_client import start_video_generation
from departments.base import audited_task
from departments.marketing_comms.aspects import ASPECTS
from shared.custom_skills import with_custom_guidance
from shared.verification import vote_aspects, votes_to_dicts

DEPARTMENT_ID = "marketing_comms"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    return build_tiered_stage_agents(
        name, instruction=_load_prompt(prompt_file), description=f"Marketing & Comms pipeline stage: {name}",
        department_id=DEPARTMENT_ID,
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
            data={
                "copy": copy,
                "brand_voice_passed": False,
                "votes": votes_to_dicts(verified.votes),
                "retried": verified.retried,
            },
            needs_human=True,
            human_question=f"Marketing copy needs a rewrite — {failed_reasons}",
        )

    schedule_suggestion = await run_agent_turn(scheduler_agents[tier], _session_service, org_id, DEPARTMENT_ID, copy)

    data = {
        "copy": copy,
        "brand_voice_passed": True,
        "schedule_suggestion": schedule_suggestion,
        "votes": votes_to_dicts(verified.votes),
        "retried": verified.retried,
    }
    summary = f"{copy}\n\nSuggested timing: {schedule_suggestion}"

    # Optional Veo promo-video generation (ADR-0019) — a deterministic
    # keyword check, not an LLM judgment call, same reasoning as every other
    # "is this mechanism warranted" decision in this app (e.g. notify_slack_
    # channel's severity check). Veo generation takes minutes, so this task
    # still completes (DONE) now with the copy — the video, if requested,
    # arrives later via app/api/veo.py's polling endpoint, which patches
    # task.result["videoUrl"] in place once ready.
    if "video" in task.description.lower():
        operation_name = await start_video_generation(org_id, copy)
        store.create_veo_operation(org_id, task.id, operation_name)
        summary += "\n\nA promo video was requested and is generating in the background — check back shortly."
        # camelCase to match videoUrl (app/api/veo.py adds that key once
        # ready) — nested result-dict keys aren't auto-camelCased the way
        # top-level Task fields are (see store.update_task), so this has to
        # be written correctly here rather than relying on that.
        data["videoGenerating"] = True

    return TaskResult(success=True, summary=summary, data=data, needs_human=False)
