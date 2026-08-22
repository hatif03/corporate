"""Covers ADR-0011's departments/base.py fixes: a department raising is
caught (never propagates to a bare 500) and surfaced through the same
human_qa mechanism as a deliberate needs_human result — which itself is
also under test here for the first time (gap #3: has_pending_human_qa was
being set without ever appending the actual question)."""

from unittest.mock import AsyncMock, patch

from app.models import Task, TaskResult, TaskStatus
from departments.base import audited_task


def _fake_task(**overrides) -> Task:
    defaults = dict(
        id="task-1", title="Do the thing", description="...", task_type="review_invoice",
        status=TaskStatus.TODO, assignee="finance_audit", created_by="ceo",
    )
    return Task(**{**defaults, **overrides})


async def test_success_path_marks_done_and_replies():
    fn = AsyncMock(return_value=TaskResult(success=True, summary="all good"))
    wrapped = audited_task("finance_audit")(fn)
    task = _fake_task()

    with (
        patch("departments.base.store.update_task") as mock_update,
        patch("departments.base.audit_chain.append_entry") as mock_audit,
        patch("departments.base.pubsub_client.publish_message") as mock_publish,
    ):
        result = await wrapped("org-test", task)

    assert result.success is True
    done_calls = [c for c in mock_update.call_args_list if c.kwargs.get("status") == TaskStatus.DONE.value]
    assert len(done_calls) == 1
    assert mock_audit.call_args.kwargs["action"] == "on_task_received"
    assert mock_publish.call_args.kwargs["act"].value == "done"


async def test_needs_human_actually_appends_a_real_question():
    fn = AsyncMock(return_value=TaskResult(success=True, summary="ok so far", needs_human=True, human_question="Approve this discount?"))
    wrapped = audited_task("sales_crm")(fn)
    task = _fake_task(assignee="sales_crm")

    with (
        patch("departments.base.store.update_task") as mock_update,
        patch("departments.base.audit_chain.append_entry"),
        patch("departments.base.pubsub_client.publish_message"),
    ):
        await wrapped("org-test", task)

    blocked_call = next(c for c in mock_update.call_args_list if c.kwargs.get("status") == TaskStatus.BLOCKED.value)
    assert blocked_call.kwargs["has_pending_human_qa"] is True
    human_qa = blocked_call.kwargs["human_qa"]
    assert len(human_qa) == 1
    assert human_qa[0]["q"] == "Approve this discount?"
    assert human_qa[0]["a"] is None


async def test_declined_task_without_needs_human_still_surfaces_a_reason():
    """A department can return success=False without needs_human=True (a
    plain decline, not a specific question) — caught live: product_analytics
    declining out-of-scope work landed as BLOCKED with no human_qa entry and
    no visible reason anywhere in the UI, since the old code only routed
    through _ask_human when needs_human was explicitly True."""
    fn = AsyncMock(return_value=TaskResult(success=False, summary="not an analytics_query, can't process"))
    wrapped = audited_task("product_analytics")(fn)
    task = _fake_task(assignee="product_analytics")

    with (
        patch("departments.base.store.update_task") as mock_update,
        patch("departments.base.audit_chain.append_entry"),
        patch("departments.base.pubsub_client.publish_message"),
    ):
        await wrapped("org-test", task)

    blocked_call = next(c for c in mock_update.call_args_list if c.kwargs.get("status") == TaskStatus.BLOCKED.value)
    assert blocked_call.kwargs["has_pending_human_qa"] is True
    assert blocked_call.kwargs["human_qa"][0]["q"] == "not an analytics_query, can't process"


async def test_department_exception_is_caught_and_surfaced_not_raised():
    fn = AsyncMock(side_effect=RuntimeError("gemini quota exceeded"))
    wrapped = audited_task("engineering_sre")(fn)
    task = _fake_task(assignee="engineering_sre")

    with (
        patch("departments.base.store.update_task") as mock_update,
        patch("departments.base.store.log_activity") as mock_log,
        patch("departments.base.audit_chain.append_entry") as mock_audit,
        patch("departments.base.pubsub_client.publish_message") as mock_publish,
    ):
        # must not raise
        result = await wrapped("org-test", task)

    assert result.success is False
    assert result.needs_human is True
    assert "gemini quota exceeded" in result.summary

    assert mock_audit.call_args.kwargs["action"] == "on_task_received_failed"
    assert mock_log.call_args.args[2] == "task-failed"

    blocked_call = next(c for c in mock_update.call_args_list if c.kwargs.get("status") == TaskStatus.BLOCKED.value)
    assert blocked_call.kwargs["has_pending_human_qa"] is True
    assert "gemini quota exceeded" in blocked_call.kwargs["human_qa"][0]["q"]

    assert mock_publish.call_args.kwargs["act"].value == "refuse"
    assert mock_publish.call_args.kwargs["needs_human"] is True
    assert mock_publish.call_args.kwargs["to"] == "ceo"  # task.created_by
