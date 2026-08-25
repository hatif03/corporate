from unittest.mock import AsyncMock, patch

from app.models import Agent, Task, TaskStatus
from departments.executive.agents import on_task_received

_DIGEST_TEXT = "Finance has one invoice done, Engineering is idle, Legal has no open work."
_ANNOUNCEMENT_TEXT = "This week: Finance closed out one invoice review; all other teams are clear."


async def test_on_task_received_publishes_digest_and_announcement():
    fake_tasks = [
        Task(
            id="t1",
            title="Review invoice",
            description="...",
            task_type="review_invoice",
            status=TaskStatus.DONE,
            assignee="finance_audit",
            created_by="ceo",
        )
    ]
    fake_agents = [
        Agent(id="ceo", name="CEO", department="executive", is_ceo=True),
        Agent(id="finance_audit", name="Finance & Audit", department="finance_audit"),
    ]

    async def fake_run_agent_turn(agent, session_service, org_id, agent_id, prompt, attachment=None):
        stage = agent.name.rsplit("_", 1)[0]
        return {"executive_digest": _DIGEST_TEXT, "executive_announcement": _ANNOUNCEMENT_TEXT}[stage]

    task = Task(
        id="task-1",
        title="Weekly digest",
        description="Produce today's company digest.",
        task_type="company_digest",
        status=TaskStatus.TODO,
        assignee="executive",
        created_by="ceo",
    )

    with (
        patch("departments.executive.agents.run_agent_turn", new=AsyncMock(side_effect=fake_run_agent_turn)),
        patch("app.services.store.list_tasks", return_value=fake_tasks),
        patch("app.services.store.list_agents", return_value=fake_agents),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is True
    assert result.needs_human is False
    assert result.summary == _ANNOUNCEMENT_TEXT
    assert result.data["digest"] == _DIGEST_TEXT
    assert result.data["snapshot"]["finance_audit"]["done"] == 1
