import json
from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.legal_risk.agents import on_task_received

CONTEXT_TEXT = (
    "Legal approved a 30-day notice requirement for any pricing change to existing customers. "
    "Acme Corp was promised no pricing changes without 30 days notice in writing."
)

TASK_DESCRIPTION = f"""STATEMENT: We're shipping the new pricing to all customers this Friday, three days from now.
CONTEXT:
{CONTEXT_TEXT}
"""

_NO_CONFLICT = json.dumps({"conflict": False})


def _judge_response(lens: str, conflict: bool, claim: str = "", evidence_quote: str = "", confidence: int = 0) -> str:
    if not conflict:
        return _NO_CONFLICT
    return json.dumps(
        {"conflict": True, "claim": claim, "evidence_quote": evidence_quote, "confidence": confidence}
    )


async def test_grounded_conflict_is_reported_and_needs_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "legal_judge_customer_promise":
            return _judge_response(
                "customer_promise",
                conflict=True,
                claim="Shipping pricing in 3 days violates the 30-day notice promised to Acme Corp.",
                evidence_quote="Acme Corp was promised no pricing changes without 30 days notice in writing.",
                confidence=90,
            )
        return _NO_CONFLICT

    with (
        patch("departments.legal_risk.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        task = Task(
            id="task-1",
            title="Check pricing rollout statement",
            description=TASK_DESCRIPTION,
            task_type="check_decision_conflict",
            status=TaskStatus.TODO,
            assignee="legal_risk",
            created_by="ceo",
        )
        result = await on_task_received("org-test", task)

    assert result.needs_human is True
    assert len(result.data["conflicts"]) == 1
    assert result.data["conflicts"][0]["lens"] == "customer_promise"


async def test_hallucinated_evidence_quote_is_dropped_not_reported():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "legal_judge_legal_compliance":
            return _judge_response(
                "legal_compliance",
                conflict=True,
                claim="This violates GDPR consent requirements.",
                evidence_quote="GDPR consent must be re-obtained for any pricing change.",  # not in CONTEXT_TEXT
                confidence=95,
            )
        return _NO_CONFLICT

    with (
        patch("departments.legal_risk.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        task = Task(
            id="task-2",
            title="Check pricing rollout statement",
            description=TASK_DESCRIPTION,
            task_type="check_decision_conflict",
            status=TaskStatus.TODO,
            assignee="legal_risk",
            created_by="ceo",
        )
        result = await on_task_received("org-test", task)

    assert result.needs_human is False
    assert result.data["conflicts"] == []


async def test_no_conflicts_at_all_is_clean():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        return _NO_CONFLICT

    with (
        patch("departments.legal_risk.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        task = Task(
            id="task-3",
            title="Check pricing rollout statement",
            description=TASK_DESCRIPTION,
            task_type="check_decision_conflict",
            status=TaskStatus.TODO,
            assignee="legal_risk",
            created_by="ceo",
        )
        result = await on_task_received("org-test", task)

    assert result.needs_human is False
    assert result.data["conflicts"] == []
