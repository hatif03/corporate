"""Engineering & SRE: triage -> cascade risk -> postmortem draft.
Incoming incident text is redacted for PII before any stage sees it (shared/
privacy_pipeline.py) — incident reports routinely contain customer emails,
phone numbers, or leaked credentials pasted in by a panicking on-call."""

from __future__ import annotations

import json
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.adk_agents.tools.universal import spawn_subagent_tool
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.engineering_sre.aspects import ASPECTS
from departments.engineering_sre.schemas import CascadePrediction, TriageResult
from departments.engineering_sre.tools import create_jira_ticket, notify_slack_channel
from shared.custom_skills import with_custom_guidance
from shared.privacy_pipeline import redact
from shared.verification import vote_aspects

DEPARTMENT_ID = "engineering_sre"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    # Opted into spawn_subagent_tool (unlike hr_people_ops/customer_support)
    # — SRE triage routinely turns up genuinely separable sub-investigations
    # worth delegating. See app/adk_agents/tools/universal.py's docstring
    # for why this can't recurse.
    return build_tiered_stage_agents(
        name,
        instruction=_load_prompt(prompt_file),
        description=f"Engineering & SRE pipeline stage: {name}",
        extra_tools=[spawn_subagent_tool],
    )


triage_agents = _build_stage_agents("sre_triage", "triage")
cascade_agents = _build_stage_agents("sre_cascade_predictor", "cascade_predictor")
postmortem_agents = _build_stage_agents("sre_postmortem_drafter", "postmortem_drafter")

_session_service = FirestoreSessionService()


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)


HIGH_SEVERITY = {"P1", "P2"}


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    redaction = redact(task.description)
    if redaction.had_pii:
        # ponytail: we only log which categories fired, never the raw
        # matches — see shared/privacy_pipeline.py's docstring.
        from app.services import store

        store.log_activity(
            org_id, DEPARTMENT_ID, "pii-redacted", f"redacted {list(redaction.found.keys())} before LLM processing"
        )

    # Stage 1: triage — the only stage that sees a vision attachment
    # (e.g. a screenshot of the error/dashboard).
    triage_text = await run_agent_turn(
        triage_agents[tier], _session_service, org_id, DEPARTMENT_ID,
        with_custom_guidance(org_id, DEPARTMENT_ID, redaction.redacted_text), attachment=task.attachment
    )
    triage = TriageResult(**_extract_json(triage_text))

    # Stage 2: cascade risk
    cascade_text = await run_agent_turn(
        cascade_agents[tier], _session_service, org_id, DEPARTMENT_ID, triage.model_dump_json()
    )
    cascade = CascadePrediction(**_extract_json(cascade_text))

    # Stage 3: postmortem draft
    postmortem_input = json.dumps({"triage": triage.model_dump(), "cascade": cascade.model_dump()})
    postmortem = await run_agent_turn(
        postmortem_agents[tier], _session_service, org_id, DEPARTMENT_ID, postmortem_input
    )

    claim = {"triage": triage.model_dump(), "cascade": cascade.model_dump()}
    verified = await vote_aspects(claim, ASPECTS)

    needs_human = triage.severity in HIGH_SEVERITY or cascade.cascade_risk == "high" or not verified.verified

    if needs_human:
        await notify_slack_channel(
            org_id,
            "#incidents",
            f"[{triage.severity}] {triage.summary} — cascade risk: {cascade.cascade_risk}",
        )
    if cascade.cascade_risk == "high":
        await create_jira_ticket(org_id, "SRE", f"[{triage.severity}] {triage.summary}", postmortem)

    return TaskResult(
        success=True,
        summary=postmortem,
        data={
            "severity": triage.severity,
            "affected_systems": triage.affected_systems,
            "cascade_risk": cascade.cascade_risk,
            "verified": verified.verified,
        },
        needs_human=needs_human,
        human_question=(
            f"Incident triaged as {triage.severity} with {cascade.cascade_risk} cascade risk — "
            "needs immediate human attention." if needs_human else None
        ),
    )
