"""Covers ADR-0012's Gemini cost guard: the store-level atomic counter and
its single call site in run_agent_turn (every agent turn — CEO and every
department pipeline stage alike — goes through that one function)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import OrgSettings
from app.services import store


def test_increment_and_check_returns_true_under_limit():
    mock_doc = MagicMock()
    mock_doc.get.return_value.to_dict.return_value = {"geminiCalls": 3}
    with patch("app.services.store.org_doc", return_value=mock_doc):
        assert store.increment_and_check_gemini_budget("org-test", daily_limit=500) is True
    mock_doc.set.assert_called_once()


def test_increment_and_check_returns_false_over_limit():
    mock_doc = MagicMock()
    mock_doc.get.return_value.to_dict.return_value = {"geminiCalls": 501}
    with patch("app.services.store.org_doc", return_value=mock_doc):
        assert store.increment_and_check_gemini_budget("org-test", daily_limit=500) is False


def test_increment_and_check_keys_by_org_and_today():
    mock_doc = MagicMock()
    mock_doc.get.return_value.to_dict.return_value = {"geminiCalls": 1}
    with patch("app.services.store.org_doc", return_value=mock_doc) as mock_org_doc:
        store.increment_and_check_gemini_budget("org-test", daily_limit=500)

    args = mock_org_doc.call_args.args
    assert args[0] == "org-test"
    assert args[1] == "usage"
    # args[2] is today's date key — just confirm it looks like YYYY-MM-DD
    assert len(args[2]) == 10 and args[2].count("-") == 2


async def test_run_agent_turn_raises_when_over_budget():
    from app.adk_agents.runtime import run_agent_turn

    with (
        patch("app.adk_agents.runtime.store.get_org_settings", return_value=OrgSettings()),
        patch("app.adk_agents.runtime.store.increment_and_check_gemini_budget", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="budget exceeded"):
            await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")


async def test_run_agent_turn_proceeds_when_under_budget():
    from app.adk_agents.runtime import run_agent_turn

    async def fake_run_async(**kwargs):
        return
        yield  # pragma: no cover - makes this an async generator with 0 items

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async

    with (
        patch("app.adk_agents.runtime.store.get_org_settings", return_value=OrgSettings()),
        patch("app.adk_agents.runtime.store.increment_and_check_gemini_budget", return_value=True),
        patch("app.adk_agents.runtime.Runner", return_value=mock_runner),
    ):
        result = await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")

    assert result == ""


async def test_run_agent_turn_uses_org_override_when_set():
    """The org's own dailyGeminiCallLimit (once set from the Settings tab,
    ADR-0013) takes precedence over the global fallback."""
    from app.adk_agents.runtime import run_agent_turn

    async def fake_run_async(**kwargs):
        return
        yield  # pragma: no cover

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async

    with (
        patch("app.adk_agents.runtime.store.get_org_settings", return_value=OrgSettings(daily_gemini_call_limit=2)),
        patch("app.adk_agents.runtime.store.increment_and_check_gemini_budget", return_value=True) as mock_check,
        patch("app.adk_agents.runtime.Runner", return_value=mock_runner),
    ):
        await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")

    assert mock_check.call_args.args[1] == 2
