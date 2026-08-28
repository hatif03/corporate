"""set_mood and propose_skill (app/adk_agents/tools/universal.py) — the two
new agent-callable tools behind the living-agent persona work. Other
universal.py tools have their own test file (test_universal_memory_tools.py);
these are new and easy to get subtly wrong (status="pending" vs "active"),
so they get one test each here, same conventions as that file.
"""

from unittest.mock import MagicMock, patch

from app.adk_agents.tools.universal import propose_skill, set_mood


def _fake_tool_context(org_id="org-test", agent_id="engineering_sre"):
    ctx = MagicMock()
    ctx.session.user_id = org_id
    ctx.session.id = agent_id
    return ctx


async def test_set_mood_writes_to_agent_doc():
    with patch("app.adk_agents.tools.universal.org_doc") as mock_org_doc:
        result = await set_mood("frustrated", tool_context=_fake_tool_context())

    assert result == {"updated": True}
    mock_org_doc.assert_called_once_with("org-test", "agents", "engineering_sre")
    mock_org_doc.return_value.update.assert_called_once_with({"mood": "frustrated"})


async def test_propose_skill_writes_as_pending_not_active():
    with patch("app.adk_agents.tools.universal.store.add_agent_custom_skill", return_value="skill-1") as mock_add:
        result = await propose_skill(
            "Always escalate P1s", "Page on-call immediately.", tool_context=_fake_tool_context()
        )

    assert result == {"proposed": True, "skill_id": "skill-1"}
    mock_add.assert_called_once_with(
        "org-test", "engineering_sre", "Always escalate P1s", "Page on-call immediately.", status="pending"
    )
