"""Customer Support: classify intent -> draft a KB-grounded reply -> verify
the cited quote is actually in the KB before sending it, escalating to a
human otherwise. Third department (after Finance & Audit and Legal & Risk)
reusing shared/verification.py's ground_quote — see docs/adr/0007."""

from __future__ import annotations

import json
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services.knowledge_base import department_kb_text
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.customer_support.knowledge_base import DEFAULT_KB_NOTE, KNOWLEDGE_BASE
from departments.customer_support.schemas import DraftResponse, IntentClassification
from shared.custom_skills import with_custom_guidance
from shared.verification import ground_quote

DEPARTMENT_ID = "customer_support"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    return build_tiered_stage_agents(
        name, instruction=_load_prompt(prompt_file), description=f"Customer Support pipeline stage: {name}",
        department_id=DEPARTMENT_ID,
    )


intent_agents = _build_stage_agents("support_intent_classifier", "intent_classifier")
response_agents = _build_stage_agents("support_response_drafter", "response_drafter")

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
    # Stage 1 is the only one that sees a vision attachment (e.g. a
    # screenshot of the issue a customer sent in).
    classification_text = await run_agent_turn(
        intent_agents[tier], _session_service, org_id, DEPARTMENT_ID,
        with_custom_guidance(org_id, DEPARTMENT_ID, task.description), attachment=task.attachment
    )
    classification = IntentClassification(**_extract_json(classification_text))

    static_article = KNOWLEDGE_BASE.get(classification.intent, DEFAULT_KB_NOTE)
    kb_article = department_kb_text(org_id, DEPARTMENT_ID, static_fallback=static_article)
    draft_input = f"KB ARTICLE:\n{kb_article}\n\nCUSTOMER MESSAGE:\n{task.description}"
    draft_text = await run_agent_turn(response_agents[tier], _session_service, org_id, DEPARTMENT_ID, draft_input)
    draft = DraftResponse(**_extract_json(draft_text))

    grounded = True
    if draft.cited_quote:
        grounded = ground_quote(draft.cited_quote, kb_article) is not None

    needs_human = (
        classification.urgency == "high"
        or not grounded
        or kb_article == DEFAULT_KB_NOTE
    )

    return TaskResult(
        success=grounded,
        summary=draft.reply,
        data={"intent": classification.intent, "urgency": classification.urgency, "grounded": grounded},
        needs_human=needs_human,
        human_question=(
            "Reply cites something not actually in the knowledge base — needs a human rewrite."
            if not grounded
            else f"High-urgency {classification.intent} ticket — needs human review before sending."
            if needs_human
            else None
        ),
    )
