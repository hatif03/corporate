"""Covers runtime.py's gated memory auto-surfacing (docs/adr/0015): a cheap
existence check before any real semantic-search call, so an agent with no
memory yet pays nothing extra on the hottest code path in the app."""

from unittest.mock import MagicMock, patch

from app.models import OrgSettings
from app.services.memory_search import MemoryHit


def _fake_run(captured: dict):
    async def fake_run_async(**kwargs):
        captured["new_message"] = kwargs["new_message"]
        return
        yield  # pragma: no cover

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async
    return mock_runner


def _patches(mock_runner):
    return (
        patch("app.adk_agents.runtime.store.get_org_settings", return_value=OrgSettings()),
        patch("app.adk_agents.runtime.store.increment_and_check_gemini_budget", return_value=True),
        patch("app.adk_agents.runtime.Runner", return_value=mock_runner),
    )


def test_relevant_memory_block_returns_none_without_calling_search_when_no_memory():
    from app.adk_agents.runtime import _relevant_memory_block

    with (
        patch("app.adk_agents.runtime.store.list_memory", return_value=[]) as mock_list,
        patch("app.adk_agents.runtime.search_memory") as mock_search,
    ):
        result = _relevant_memory_block("org-test", "finance_audit", "do the thing")

    assert result is None
    mock_list.assert_called_once_with("org-test", "finance_audit", limit_count=1)
    mock_search.assert_not_called()


def test_relevant_memory_block_returns_none_when_search_finds_nothing():
    with (
        patch("app.adk_agents.runtime.store.list_memory", return_value=[{"id": "m1"}]),
        patch("app.adk_agents.runtime.search_memory", return_value=[]),
    ):
        from app.adk_agents.runtime import _relevant_memory_block

        assert _relevant_memory_block("org-test", "finance_audit", "do the thing") is None


def test_relevant_memory_block_formats_hits():
    hits = [MemoryHit(agent_id="finance_audit", memory_id="m1", text="vendor risk flagged last quarter", score=0.9)]
    with (
        patch("app.adk_agents.runtime.store.list_memory", return_value=[{"id": "m1"}]),
        patch("app.adk_agents.runtime.search_memory", return_value=hits) as mock_search,
    ):
        from app.adk_agents.runtime import _relevant_memory_block

        result = _relevant_memory_block("org-test", "finance_audit", "check this vendor")

    assert result is not None
    assert "vendor risk flagged last quarter" in result
    mock_search.assert_called_once_with("org-test", "check this vendor", agent_id="finance_audit", top_k=3)


async def test_run_agent_turn_prepends_memory_block_when_present():
    from app.adk_agents.runtime import run_agent_turn

    captured: dict = {}
    mock_runner = _fake_run(captured)
    p1, p2, p3 = _patches(mock_runner)
    with (
        p1,
        p2,
        p3,
        patch("app.adk_agents.runtime._relevant_memory_block", return_value="Relevant memory from your own past notes:\n- old fact"),
    ):
        await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")

    sent_text = captured["new_message"].parts[0].text
    assert "old fact" in sent_text
    assert "do the thing" in sent_text


async def test_run_agent_turn_sends_prompt_unchanged_when_no_memory():
    from app.adk_agents.runtime import run_agent_turn

    captured: dict = {}
    mock_runner = _fake_run(captured)
    p1, p2, p3 = _patches(mock_runner)
    with p1, p2, p3, patch("app.adk_agents.runtime._relevant_memory_block", return_value=None):
        await run_agent_turn(MagicMock(), MagicMock(), "org-test", "finance_audit", "do the thing")

    assert captured["new_message"].parts[0].text == "do the thing"
