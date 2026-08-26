from unittest.mock import MagicMock, patch

from app.adk_agents.tools.universal import read_memory, search_memory_tool, write_memory


def _fake_tool_context(org_id="org-test", agent_id="finance_audit"):
    ctx = MagicMock()
    ctx.session.user_id = org_id
    ctx.session.id = agent_id
    return ctx


async def test_write_memory_embeds_and_appends():
    with (
        patch("app.adk_agents.tools.universal.embed_text", return_value=[0.1, 0.2]) as mock_embed,
        patch("app.adk_agents.tools.universal.store.append_memory", return_value="mem-1") as mock_append,
    ):
        result = await write_memory("learned something", tool_context=_fake_tool_context())

    assert result == {"saved": True, "memory_id": "mem-1"}
    mock_embed.assert_called_once_with("learned something")
    mock_append.assert_called_once_with("org-test", "finance_audit", "learned something", [0.1, 0.2])


async def test_read_memory_returns_recent_entries_oldest_first():
    entries = [
        {"id": "m2", "text": "second note"},
        {"id": "m1", "text": "first note"},
    ]  # store.list_memory returns newest-first
    with patch("app.adk_agents.tools.universal.store.list_memory", return_value=entries):
        result = await read_memory(tool_context=_fake_tool_context())

    assert result == "- first note\n- second note"


async def test_read_memory_returns_empty_string_when_no_history():
    with patch("app.adk_agents.tools.universal.store.list_memory", return_value=[]):
        result = await read_memory(tool_context=_fake_tool_context())

    assert result == ""


async def test_search_memory_tool_formats_hits_by_score():
    from app.services.memory_search import MemoryHit

    hits = [MemoryHit(agent_id="finance_audit", memory_id="m1", text="Q3 vendor risk flagged", score=0.91)]
    with patch("app.adk_agents.tools.universal._search_memory", return_value=hits) as mock_search:
        result = await search_memory_tool("vendor risk", tool_context=_fake_tool_context())

    assert "0.91" in result and "Q3 vendor risk flagged" in result
    mock_search.assert_called_once_with("org-test", "vendor risk", agent_id="finance_audit", top_k=5)


async def test_search_memory_tool_returns_empty_string_on_no_hits():
    with patch("app.adk_agents.tools.universal._search_memory", return_value=[]):
        assert await search_memory_tool("x", tool_context=_fake_tool_context()) == ""
