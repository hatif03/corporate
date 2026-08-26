"""Covers runtime.py's per-turn tool-call step cap and doom-loop guard
(adapted from opencode's doom-loop detector, MIT — see /THIRD_PARTY_SKILLS.md
and docs/adr/0015). A RuntimeError here is caught by @audited_task's
existing failure path (ADR-0011) — this test only needs to prove the guard
actually fires (and doesn't false-positive), not re-test that path."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models import OrgSettings


def _fake_event(*function_calls, final_text=None):
    event = MagicMock()
    event.get_function_calls.return_value = list(function_calls)
    event.is_final_response.return_value = final_text is not None
    if final_text is not None:
        event.content.parts = [SimpleNamespace(text=final_text)]
    return event


def _call(name: str, args: dict) -> SimpleNamespace:
    return SimpleNamespace(name=name, args=args)


def _patched_run(events):
    async def fake_run_async(**kwargs):
        for event in events:
            yield event

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async
    return (
        patch("app.adk_agents.runtime.store.get_org_settings", return_value=OrgSettings()),
        patch("app.adk_agents.runtime.store.increment_and_check_gemini_budget", return_value=True),
        patch("app.adk_agents.runtime.Runner", return_value=mock_runner),
    )


async def test_identical_tool_call_three_times_in_a_row_raises():
    from app.adk_agents.runtime import run_agent_turn

    events = [_fake_event(_call("read_memory", {"q": "x"})) for _ in range(3)]
    p1, p2, p3 = _patched_run(events)
    with p1, p2, p3:
        with pytest.raises(RuntimeError, match="stuck loop"):
            await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")


async def test_two_identical_then_different_call_does_not_raise():
    from app.adk_agents.runtime import run_agent_turn

    events = [
        _fake_event(_call("read_memory", {"q": "x"})),
        _fake_event(_call("read_memory", {"q": "x"})),
        _fake_event(_call("read_memory", {"q": "y"})),
        _fake_event(final_text="done"),
    ]
    p1, p2, p3 = _patched_run(events)
    with p1, p2, p3:
        result = await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")
    assert result == "done"


async def test_exceeding_max_tool_calls_raises():
    from app.adk_agents.runtime import MAX_TOOL_CALLS_PER_TURN, run_agent_turn

    events = [_fake_event(_call("read_memory", {"q": str(i)})) for i in range(MAX_TOOL_CALLS_PER_TURN + 1)]
    p1, p2, p3 = _patched_run(events)
    with p1, p2, p3:
        with pytest.raises(RuntimeError, match="exceeded"):
            await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")
