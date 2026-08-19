from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.product_analytics.agents import on_task_received


def _fake_tasks() -> list[Task]:
    return [
        Task(
            id="t1", title="a", description="", task_type="review_invoice",
            status=TaskStatus.DONE, assignee="finance_audit", created_by="ceo",
        ),
        Task(
            id="t2", title="b", description="", task_type="review_invoice",
            status=TaskStatus.DOING, assignee="finance_audit", created_by="ceo",
        ),
        Task(
            id="t3", title="c", description="", task_type="handle_incident",
            status=TaskStatus.BLOCKED, assignee="engineering_sre", created_by="ceo",
        ),
    ]


async def test_chart_is_built_deterministically_from_real_counts():
    task = Task(
        id="task-1",
        title="How many tasks are open per department?",
        description="How many tasks does each department currently have open?",
        task_type="analytics_query",
        status=TaskStatus.TODO,
        assignee="product_analytics",
        created_by="ceo",
    )

    with (
        patch(
            "departments.product_analytics.agents.run_agent_turn",
            new=AsyncMock(return_value="Finance & Audit has 1 done and 1 in progress; Engineering has 1 blocked."),
        ),
        patch("app.services.store.list_tasks", return_value=_fake_tasks()),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is True
    assert result.needs_human is False
    assert result.data["raw_counts"]["finance_audit"]["done"] == 1
    assert result.data["raw_counts"]["finance_audit"]["doing"] == 1
    assert result.data["raw_counts"]["engineering_sre"]["blocked"] == 1

    chart = result.data["chart"]
    assert chart["chart_type"] == "bar"
    assert sorted(chart["labels"]) == ["engineering_sre", "finance_audit"]
    finance_idx = chart["labels"].index("finance_audit")
    assert chart["series"]["done"][finance_idx] == 1
