import json
from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.customer_support.agents import on_task_received


def _make_task(description: str) -> Task:
    return Task(
        id="task-1",
        title="Support ticket",
        description=description,
        task_type="support_ticket",
        status=TaskStatus.TODO,
        assignee="customer_support",
        created_by="ceo",
    )


async def test_grounded_low_urgency_reply_succeeds_without_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "support_intent_classifier":
            return json.dumps({"intent": "billing", "urgency": "low"})
        return json.dumps(
            {
                "reply": "You can get a refund since it's within 14 days of purchase.",
                "cited_quote": "Refunds are issued for cancellations requested within 14 days of purchase.",
            }
        )

    with (
        patch("departments.customer_support.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("Can I get a refund? I bought this 3 days ago."))

    assert result.success is True
    assert result.needs_human is False
    assert result.data["grounded"] is True


async def test_hallucinated_citation_escalates_to_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "support_intent_classifier":
            return json.dumps({"intent": "billing", "urgency": "low"})
        return json.dumps(
            {
                "reply": "We offer refunds for up to 90 days after purchase.",
                "cited_quote": "Refunds are available for up to 90 days after purchase.",  # not in the real KB
            }
        )

    with (
        patch("departments.customer_support.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("What's your refund window?"))

    assert result.success is False
    assert result.needs_human is True
    assert result.data["grounded"] is False


async def test_high_urgency_ticket_escalates_even_when_grounded():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "support_intent_classifier":
            return json.dumps({"intent": "technical", "urgency": "high"})
        return json.dumps(
            {
                "reply": "The API rate limit is 100 requests per minute per key.",
                "cited_quote": "The API rate limit is 100 requests per minute per API key.",
            }
        )

    with (
        patch("departments.customer_support.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("Our production integration is completely down!"))

    assert result.needs_human is True
    assert result.data["grounded"] is True
