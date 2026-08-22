"""Regression test for the ADK callback-parameter-name bug caught live:
google-adk 2.7.1 dispatches these callbacks by keyword, with an enforced
name per callback type (callback_context / tool_context, not a generic
`context`) — a mismatch raises TypeError at call time, not at registration,
so nothing short of actually invoking them this way catches it."""

from unittest.mock import MagicMock, patch

import pytest

from app.adk_agents import callbacks


def _fake_context(org_id: str = "demo", agent_id: str = "ceo") -> MagicMock:
    ctx = MagicMock()
    ctx.session.user_id = org_id
    ctx.session.id = agent_id
    return ctx


async def test_before_agent_callback_matches_adks_enforced_keyword():
    with patch("app.adk_agents.callbacks.store.update_agent_status") as mock_update:
        await callbacks.before_agent_callback(callback_context=_fake_context())
    assert mock_update.call_args.args[:2] == ("demo", "ceo")


async def test_after_agent_callback_matches_adks_enforced_keyword():
    with patch("app.adk_agents.callbacks.store.update_agent_status") as mock_update:
        await callbacks.after_agent_callback(callback_context=_fake_context())
    assert mock_update.call_args.args[:2] == ("demo", "ceo")


async def test_before_tool_callback_matches_adks_enforced_keywords():
    tool = MagicMock(name="send_message")
    tool.name = "send_message"
    with patch("app.adk_agents.callbacks.store.update_agent_status") as mock_update:
        await callbacks.before_tool_callback(tool=tool, args={"to": "ceo"}, tool_context=_fake_context())
    assert mock_update.call_args.args[:2] == ("demo", "ceo")


async def test_after_tool_callback_matches_adks_enforced_keywords():
    tool = MagicMock(name="send_message")
    tool.name = "send_message"
    with (
        patch("app.adk_agents.callbacks.store.append_trace") as mock_trace,
        patch("app.adk_agents.callbacks.store.update_agent_status"),
    ):
        await callbacks.after_tool_callback(
            tool=tool, args={"to": "ceo"}, tool_context=_fake_context(), tool_response={"ok": True}
        )
    assert mock_trace.call_args.args[:2] == ("demo", "ceo")
