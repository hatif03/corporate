"""Engineering & SRE: triage -> cascade risk -> postmortem draft.
Incoming incident text is redacted for PII before any stage sees it (shared/
privacy_pipeline.py) — incident reports routinely contain customer emails,
phone numbers, or leaked credentials pasted in by a panicking on-call."""

from __future__ import annotations

import json
from pathlib import Path

from google.adk.agents.llm_agent import LlmAgent

from app.adk_agents.factory import department_callbacks, department_tools
from app.adk_agents.runtime import run_agent_turn
from app.config import settings
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.engineering_sre.schemas import CascadePrediction, TriageResult
from shared.privacy_pipeline import redact

DEPARTMENT_ID = "engineering_sre"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agent(name: str, prompt_file: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=settings.corporate_gemini_model,
        instruction=_load_prompt(prompt_file),
        description=f"Engineering & SRE pipeline stage: {name}",
        tools=department_tools(),
        **department_callbacks(),
    )


triage_agent = _build_stage_agent("sre_triage", "triage")
cascade_agent = _build_stage_agent("sre_cascade_predictor", "cascade_predictor")
postmortem_agent = _build_stage_agent("sre_postmortem_drafter", "postmortem_drafter")

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
    redaction = redact(task.description)
    if redaction.had_pii:
        # ponytail: we only log which categories fired, never the raw
        # matches — see shared/privacy_pipeline.py's docstring.
        from app.services import store

        store.log_activity(
            org_id, DEPARTMENT_ID, "pii-redacted", f"redacted {list(redaction.found.keys())} before LLM processing"
        )

    # Stage 1: triage
    triage_text = await run_agent_turn(
        triage_agent, _session_service, org_id, DEPARTMENT_ID, redaction.redacted_text
    )
    triage = TriageResult(**_extract_json(triage_text))

    # Stage 2: cascade risk
    cascade_text = await run_agent_turn(
        cascade_agent, _session_service, org_id, DEPARTMENT_ID, triage.model_dump_json()
    )
    cascade = CascadePrediction(**_extract_json(cascade_text))

    # Stage 3: postmortem draft
    postmortem_input = json.dumps({"triage": triage.model_dump(), "cascade": cascade.model_dump()})
    postmortem = await run_agent_turn(
        postmortem_agent, _session_service, org_id, DEPARTMENT_ID, postmortem_input
    )

    needs_human = triage.severity in HIGH_SEVERITY or cascade.cascade_risk == "high"

    return TaskResult(
        success=True,
        summary=postmortem,
        data={
            "severity": triage.severity,
            "affected_systems": triage.affected_systems,
            "cascade_risk": cascade.cascade_risk,
        },
        needs_human=needs_human,
        human_question=(
            f"Incident triaged as {triage.severity} with {cascade.cascade_risk} cascade risk — "
            "needs immediate human attention." if needs_human else None
        ),
    )
