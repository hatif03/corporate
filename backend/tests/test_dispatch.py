"""Covers ADR-0011: idempotency on Pub/Sub redelivery, and that dispatch
never lets an exception escape (the general safety-net path — a
department's own failure path is covered by
departments/tests/test_base.py instead)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Act, Message
from app.services.dispatch import handle_agent_turn


def _fake_message(**overrides) -> Message:
    defaults = dict(
        id="msg-1",
        conversation="task-1",
        from_="ceo",
        to="finance_audit",
        act=Act.REQUEST,
        subject="do the thing",
        body="...",
        requires_reply=True,
    )
    return Message(**{**defaults, **overrides})


async def test_duplicate_message_is_a_no_op():
    department = MagicMock()
    department.on_task_received = AsyncMock()

    with (
        patch("app.services.dispatch.store.mark_message_processed", return_value=False) as mock_mark,
        patch("app.services.dispatch.store.log_activity") as mock_log,
        patch("app.services.dispatch.get_department", return_value=department),
        patch("app.services.dispatch.store.get_task") as mock_get_task,
    ):
        await handle_agent_turn("org-test", "finance_audit", _fake_message())

    assert mock_mark.called
    assert not department.on_task_received.called
    assert not mock_get_task.called
    assert mock_log.call_args.args[2] == "duplicate-skipped"


async def test_first_delivery_runs_the_pipeline_once():
    department = MagicMock()
    department.on_task_received = AsyncMock()
    fake_task = MagicMock()

    with (
        patch("app.services.dispatch.store.mark_message_processed", return_value=True),
        patch("app.services.dispatch.get_department", return_value=department),
        patch("app.services.dispatch.store.get_task", return_value=fake_task),
    ):
        await handle_agent_turn("org-test", "finance_audit", _fake_message())

    department.on_task_received.assert_awaited_once_with("org-test", fake_task)


async def test_unexpected_exception_is_caught_and_logged_not_raised():
    with (
        patch("app.services.dispatch.store.mark_message_processed", return_value=True),
        patch("app.services.dispatch.get_department", side_effect=RuntimeError("boom")),
        patch("app.services.dispatch.store.log_activity") as mock_log,
    ):
        # must not raise — this is the whole point of the safety net
        await handle_agent_turn("org-test", "finance_audit", _fake_message())

    assert mock_log.call_args.args[2] == "dispatch-failed"


async def test_ceo_turn_exception_is_caught_and_logged_not_raised():
    with (
        patch("app.services.dispatch.store.mark_message_processed", return_value=True),
        patch("app.services.dispatch.get_department", return_value=None),
        patch("app.services.dispatch.run_agent_turn", new=AsyncMock(side_effect=RuntimeError("gemini timeout"))),
        patch("app.services.dispatch.store.log_activity") as mock_log,
    ):
        await handle_agent_turn("org-test", "ceo", _fake_message(to="ceo", act=Act.INFORM, requires_reply=False))

    assert mock_log.call_args.args[2] == "dispatch-failed"
