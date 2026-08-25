"""Finance & Audit: extract -> classify -> fraud-check -> verify -> explain.
See docs/adr/0006-gemini-only-fraud-agent-structural-independence.md for why
the fraud stage is split the way it is."""

from __future__ import annotations

import json
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
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


def _build_stage_agents(name: str, prompt_file: str) -> dict:
    return build_tiered_stage_agents(
        name, instruction=_load_prompt(prompt_file), description=f"Finance & Audit pipeline stage: {name}"
    )


doc_intel_agents = _build_stage_agents("finance_doc_intel", "doc_intel")
accountant_agents = _build_stage_agents("finance_accountant", "accountant")
fraud_agents = _build_stage_agents("finance_fraud", "fraud")
explainer_agents = _build_stage_agents("finance_explainer", "explainer")

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
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    # Stage 1: document intelligence — the only stage that sees a vision
    # attachment (an invoice image), consistent with ADR-0006's fraud-stage
    # isolation: the fraud stage below still only ever sees signals JSON.
    doc_intel_text = await run_agent_turn(
        doc_intel_agents[tier], _session_service, org_id, DEPARTMENT_ID, task.description, attachment=task.attachment
    )
    invoice = InvoiceFields(**_extract_json(doc_intel_text))

    # Stage 2: accountant classification (never shown to the fraud stage)
    classification = await run_agent_turn(
        accountant_agents[tier], _session_service, org_id, DEPARTMENT_ID, invoice.model_dump_json()
    )

    # Stage 3a: deterministic fraud signals, zero LLM calls
    fraud_signals = signals.compute_signals(org_id, invoice)

    # Stage 3b: fraud LLM call sees ONLY the signals JSON — see the module docstring
    fraud_text = await run_agent_turn(
        fraud_agents[tier], _session_service, org_id, DEPARTMENT_ID, fraud_signals.model_dump_json()
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
        explainer_agents[tier], _session_service, org_id, DEPARTMENT_ID, explainer_input
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
