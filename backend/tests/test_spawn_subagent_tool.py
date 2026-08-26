from unittest.mock import AsyncMock, MagicMock, patch

from app.adk_agents.tools.universal import spawn_subagent_tool


def _fake_tool_context(org_id="org-test", agent_id="ceo"):
    ctx = MagicMock()
    ctx.session.user_id = org_id
    ctx.session.id = agent_id
    return ctx


async def test_spawn_subagent_tool_delegates_to_spawn_worker_and_await():
    with patch(
        "app.services.workers.spawn_worker_and_await",
        new=AsyncMock(return_value={"worker_id": "worker-abc", "reply": "sub-agent's real answer"}),
    ) as mock_spawn:
        result = await spawn_subagent_tool(
            "research the thing", tool_context=_fake_tool_context(), target_department="engineering_sre"
        )

    assert result == {"worker_id": "worker-abc", "reply": "sub-agent's real answer"}
    mock_spawn.assert_called_once_with(
        "org-test", source_event="subagent-of-ceo", prompt="research the thing", target_agent="engineering_sre", model_tier="flash"
    )


async def test_spawn_subagent_tool_never_reaches_worker_agents():
    """Depth cap is structural: spawn_subagent_tool must never end up in the
    tool list ephemeral worker agents themselves get, or a sub-agent could
    spawn another sub-agent."""
    from app.services.workers import _worker_agents

    for agent in _worker_agents.values():
        tool_names = {getattr(t, "__name__", getattr(t, "name", None)) for t in agent.tools}
        assert "spawn_subagent_tool" not in tool_names
