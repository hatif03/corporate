"""app/adk_agents/factory.py — two confirmed real gaps from this session's
production audit: every agent has google_search_tool but nothing ever told
a model when to use it, and the CEO had set_mood but not propose_skill (an
unexplained asymmetry with every department, which gets both)."""

from app.adk_agents.factory import _CEO_TOOLS, build_ceo_agent, build_tiered_stage_agents
from app.adk_agents.tools.universal import propose_skill


def test_ceo_has_propose_skill_same_as_every_department():
    assert propose_skill in _CEO_TOOLS


def test_ceo_agent_instruction_includes_search_guidance():
    agent = build_ceo_agent()
    assert "Google Search" in agent.instruction


def test_department_stage_instruction_includes_search_guidance():
    agents_by_tier = build_tiered_stage_agents("test_stage", instruction="Do the thing.", description="test")
    assert "Google Search" in agents_by_tier["flash"].instruction
    assert "Do the thing." in agents_by_tier["flash"].instruction
