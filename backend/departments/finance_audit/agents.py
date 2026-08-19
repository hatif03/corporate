"""Finance & Audit: extract -> classify -> fraud-check -> verify -> explain.
See docs/adr/0006-gemini-only-fraud-agent-structural-independence.md for why
the fraud stage is split the way it is."""

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
from departments.finance_audit import signals
from departments.finance_audit.aspects import ASPECTS
from departments.finance_audit.schemas import FraudSignals, InvoiceFields
from shared.verification import vote_aspects

DEPARTMENT_ID = "finance_audit"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agent(name: str, prompt_file: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=settings.corporate_gemini_model,
        instruction=_load_prompt(prompt_file),
        description=f"Finance & Audit pipeline stage: {name}",
        tools=department_tools(),
        **department_callbacks(),
    )


doc_intel_agent = _build_stage_agent("finance_doc_intel", "doc_intel")
accountant_agent = _build_stage_agent("finance_accountant", "accountant")
fraud_agent = _build_stage_agent("finance_fraud", "fraud")
explainer_agent = _build_stage_agent("finance_explainer", "explainer")

# All four stages share the department's own session (session_id ==
# DEPARTMENT_ID) so their status/trace all land on the same office-floor
# avatar — see app/adk_agents/runtime.py's module docstring.
_session_service = FirestoreSessionService()


def _extract_json(text: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences despite instructions not
    to — strip those before parsing rather than failing the whole pipeline."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    # Stage 1: document intelligence
    doc_intel_text = await run_agent_turn(
        doc_intel_agent, _session_service, org_id, DEPARTMENT_ID, task.description
    )
    invoice = InvoiceFields(**_extract_json(doc_intel_text))

    # Stage 2: accountant classification (never shown to the fraud stage)
    classification = await run_agent_turn(
        accountant_agent, _session_service, org_id, DEPARTMENT_ID, invoice.model_dump_json()
    )

    # Stage 3a: deterministic fraud signals, zero LLM calls
    fraud_signals = signals.compute_signals(org_id, invoice)

    # Stage 3b: fraud LLM call sees ONLY the signals JSON — see the module docstring
    fraud_text = await run_agent_turn(
        fraud_agent, _session_service, org_id, DEPARTMENT_ID, fraud_signals.model_dump_json()
    )
    fraud_verdict = _extract_json(fraud_text)
    risk_score = int(fraud_verdict.get("risk_score", 0))

    # Stage 4: deterministic verification (shared/verification.py)
    claim = {"invoice": invoice.model_dump(), "signals": fraud_signals.model_dump()}
    verified = await vote_aspects(claim, ASPECTS)

    needs_human = risk_score >= 60 or not verified.verified

    # Stage 5: plain-language explanation
    explainer_input = json.dumps(
        {
            "invoice": invoice.model_dump(),
            "classification": classification,
            "fraud_verdict": fraud_verdict,
            "verification_passed": verified.verified,
        }
    )
    explanation = await run_agent_turn(
        explainer_agent, _session_service, org_id, DEPARTMENT_ID, explainer_input
    )

    return TaskResult(
        success=not needs_human,
        summary=explanation,
        data={
            "vendor": invoice.vendor,
            "invoice_number": invoice.invoice_number,
            "amount": invoice.amount,
            "risk_score": risk_score,
            "verified": verified.verified,
        },
        needs_human=needs_human,
        human_question=(
            f"Invoice {invoice.invoice_number} from {invoice.vendor} needs review "
            f"(risk score {risk_score}, verification {'passed' if verified.verified else 'failed'})."
            if needs_human
            else None
        ),
    )
