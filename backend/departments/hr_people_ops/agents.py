"""HR & People Ops: classify the request -> answer against the handbook.
Leave requests always come back needing human (HR) approval — this
department explains policy, it never approves time off itself. Employee
requests are redacted for PII before either stage sees them, same pattern
as engineering_sre (shared/privacy_pipeline.py)."""

from __future__ import annotations

import json
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.hr_people_ops.handbook import HR_HANDBOOK
from departments.hr_people_ops.schemas import RequestClassification
from shared.privacy_pipeline import redact

DEPARTMENT_ID = "hr_people_ops"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    return build_tiered_stage_agents(
        name, instruction=_load_prompt(prompt_file), description=f"HR & People Ops pipeline stage: {name}"
    )


intake_agents = _build_stage_agents("hr_intake_classifier", "intake_classifier")
handbook_qa_agents = _build_stage_agents("hr_handbook_qa", "handbook_qa")

_session_service = FirestoreSessionService()


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    redaction = redact(task.description)

    classification_text = await run_agent_turn(
        intake_agents[tier], _session_service, org_id, DEPARTMENT_ID, redaction.redacted_text,
        attachment=task.attachment,
    )
    classification = RequestClassification(**_extract_json(classification_text))

    qa_input = f"HANDBOOK:\n{HR_HANDBOOK}\n\nREQUEST ({classification.request_type}): {classification.summary}"
    answer = await run_agent_turn(handbook_qa_agents[tier], _session_service, org_id, DEPARTMENT_ID, qa_input)

    needs_human = classification.request_type == "leave_request"

    return TaskResult(
        success=True,
        summary=answer,
        data={"request_type": classification.request_type},
        needs_human=needs_human,
        human_question=(f"Leave request needs HR approval: {classification.summary}" if needs_human else None),
    )
