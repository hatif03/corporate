"""Customer Support: classify intent -> draft a KB-grounded reply -> verify
the cited quote is actually in the KB before sending it, escalating to a
human otherwise. Third department (after Finance & Audit and Legal & Risk)
reusing shared/verification.py's ground_quote — see docs/adr/0007."""

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
from departments.customer_support.knowledge_base import DEFAULT_KB_NOTE, KNOWLEDGE_BASE
from departments.customer_support.schemas import DraftResponse, IntentClassification
from shared.verification import ground_quote

DEPARTMENT_ID = "customer_support"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agent(name: str, prompt_file: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=settings.corporate_gemini_model,
        instruction=_load_prompt(prompt_file),
        description=f"Customer Support pipeline stage: {name}",
        tools=department_tools(),
        **department_callbacks(),
    )


intent_agent = _build_stage_agent("support_intent_classifier", "intent_classifier")
response_agent = _build_stage_agent("support_response_drafter", "response_drafter")

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
    classification_text = await run_agent_turn(
        intent_agent, _session_service, org_id, DEPARTMENT_ID, task.description
    )
    classification = IntentClassification(**_extract_json(classification_text))

    kb_article = KNOWLEDGE_BASE.get(classification.intent, DEFAULT_KB_NOTE)
    draft_input = f"KB ARTICLE:\n{kb_article}\n\nCUSTOMER MESSAGE:\n{task.description}"
    draft_text = await run_agent_turn(response_agent, _session_service, org_id, DEPARTMENT_ID, draft_input)
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
