"""A paused agent must never silently process a task or hang it at DOING —
audited_task's pause check reuses the same BLOCKED+HumanQA+REFUSE failure
path as any other on_task_received exception (see departments/base.py)."""

from unittest.mock import AsyncMock, patch

from app.models import Agent, Task, TaskResult, TaskStatus
from departments.base import audited_task

_TASK = Task(
    id="task-1",
    title="Do a thing",
    description="...",
    task_type="test_task",
    status=TaskStatus.TODO,
    assignee="fake_dept",
    created_by="ceo",
)


async def test_paused_agent_blocks_task_without_running_the_department():
    inner = AsyncMock(side_effect=lambda org_id, task: TaskResult(success=True, summary="did the thing"))
    with (
        patch("departments.base.store.get_agent", return_value=Agent(id="fake_dept", name="x", department="fake_dept", paused=True)),
        patch("departments.base.store.update_task") as mock_update_task,
        patch("departments.base.store.log_activity"),
        patch("departments.base.audit_chain.append_entry"),
        patch("departments.base.pubsub_client.publish_message") as mock_publish,
    ):
        result = await audited_task("fake_dept")(inner)("demo", _TASK)

    inner.assert_not_awaited()
    assert result.success is False
    assert result.needs_human is True
    assert mock_update_task.call_args.kwargs["status"] == TaskStatus.BLOCKED.value
    assert mock_publish.call_args.kwargs["act"].value == "refuse"


async def test_unpaused_agent_runs_normally():
    inner = AsyncMock(side_effect=lambda org_id, task: TaskResult(success=True, summary="did the thing"))
    with (
        patch("departments.base.store.get_agent", return_value=Agent(id="fake_dept", name="x", department="fake_dept", paused=False)),
        patch("departments.base.store.update_task"),
        patch("departments.base.store.log_activity"),
        patch("departments.base.audit_chain.append_entry"),
        patch("departments.base.pubsub_client.publish_message"),
    ):
        result = await audited_task("fake_dept")(inner)("demo", _TASK)

    inner.assert_awaited_once()
    assert result.success is True
