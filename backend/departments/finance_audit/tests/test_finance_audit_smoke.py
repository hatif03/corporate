"""Smoke test for the Finance & Audit department: exercises on_task_received
end to end with the three Gemini calls mocked (no live credentials needed)
and Firestore-touching calls in the base decorator mocked out."""

import json
from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.finance_audit.agents import on_task_received

_DOC_INTEL_RESPONSE = json.dumps(
    {
        "vendor": "Acme Supplies",
        "invoice_number": "INV-1042",
        "amount": 4200.00,
        "currency": "USD",
        "line_item_amounts": [2000.00, 2200.00],
    }
)
_ACCOUNTANT_RESPONSE = "Standard operating expense, office supplies vendor, nothing unusual."
_FRAUD_RESPONSE = json.dumps({"risk_score": 15, "justification": "no signals fired"})
_EXPLAINER_RESPONSE = "This invoice looks routine and does not need human review."


async def _fake_run_agent_turn(agent, session_service, org_id, agent_id, prompt):
    # Route by which prompt-file's instruction the agent was built with —
    # simplest is to key off agent.name, set in agents.py's _build_stage_agent.
    return {
        "finance_doc_intel": _DOC_INTEL_RESPONSE,
        "finance_accountant": _ACCOUNTANT_RESPONSE,
        "finance_fraud": _FRAUD_RESPONSE,
        "finance_explainer": _EXPLAINER_RESPONSE,
    }[agent.name]


async def test_on_task_received_clean_invoice_completes_without_human_review():
    task = Task(
        id="task-1",
        title="Review invoice INV-1042",
        description="Acme Supplies invoice INV-1042 for $4200.00, two line items of $2000 and $2200.",
        task_type="review_invoice",
        status=TaskStatus.TODO,
        assignee="finance_audit",
        created_by="ceo",
    )

    with (
        patch("departments.finance_audit.agents.run_agent_turn", new=AsyncMock(side_effect=_fake_run_agent_turn)),
        patch("departments.finance_audit.signals.store.list_tasks", return_value=[]),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is True
    assert result.needs_human is False
    assert result.data["vendor"] == "Acme Supplies"
    assert result.data["risk_score"] == 15
    assert result.data["verified"] is True
    assert "does not need human review" in result.summary


async def test_on_task_received_flags_high_fraud_risk_for_human_review():
    task = Task(
        id="task-2",
        title="Review invoice INV-9999",
        description="Shell Co invoice INV-9999 for $10000.00, one line item of $10000.",
        task_type="review_invoice",
        status=TaskStatus.TODO,
        assignee="finance_audit",
        created_by="ceo",
    )

    async def fake_run_agent_turn_high_risk(agent, session_service, org_id, agent_id, prompt):
        if agent.name == "finance_doc_intel":
            return json.dumps(
                {
                    "vendor": "Shell Co",
                    "invoice_number": "INV-9999",
                    "amount": 10000.00,
                    "currency": "USD",
                    "line_item_amounts": [10000.00],
                }
            )
        if agent.name == "finance_fraud":
            return json.dumps({"risk_score": 85, "justification": "round number and single line item"})
        if agent.name == "finance_accountant":
            return _ACCOUNTANT_RESPONSE
        return "This invoice needs human review due to a high fraud risk score."

    with (
        patch(
            "departments.finance_audit.agents.run_agent_turn",
            new=AsyncMock(side_effect=fake_run_agent_turn_high_risk),
        ),
        patch("departments.finance_audit.signals.store.list_tasks", return_value=[]),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.needs_human is True
    assert result.data["risk_score"] == 85
    assert "needs review" in result.human_question
