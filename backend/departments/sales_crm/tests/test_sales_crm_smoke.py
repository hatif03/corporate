from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.sales_crm.agents import on_task_received


async def test_on_task_received_returns_outreach_draft():
    task = Task(
        id="task-1",
        title="Qualify inbound lead",
        description="Mid-size logistics company, 200 employees, asking about our routing API, wants a demo this week.",
        task_type="qualify_lead",
        status=TaskStatus.TODO,
        assignee="sales_crm",
        created_by="ceo",
    )

    with (
        patch(
            "departments.sales_crm.agents.run_agent_turn",
            new=AsyncMock(return_value="Hi there — happy to set up a demo this week, here's a 15% discount to start."),
        ),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is True
    assert "demo" in result.summary
    assert result.data["draft"] == result.summary


def test_pricing_guardrail_caps_above_max():
    import asyncio

    from departments.sales_crm.tools import MAX_DISCOUNT_PERCENT, pricing_guardrail

    result = asyncio.run(pricing_guardrail(35, tool_context=None))
    assert result["approved_percent"] == MAX_DISCOUNT_PERCENT
    assert result["capped"] is True


def test_pricing_guardrail_allows_below_max():
    import asyncio

    from departments.sales_crm.tools import pricing_guardrail

    result = asyncio.run(pricing_guardrail(10, tool_context=None))
    assert result["approved_percent"] == 10
    assert result["capped"] is False
