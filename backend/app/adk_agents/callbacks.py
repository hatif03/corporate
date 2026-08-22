"""ADK lifecycle callbacks -> Firestore -> office-floor UI.

This is the entire mechanism behind "watch your employee work": every agent
in this project is built with these four callbacks attached (see factory.py),
so the frontend's onSnapshot listeners on `agents/{id}` and
`agents/{id}/trace` update live without any bespoke event bus.

In this project session.id is always the agent id and session.user_id is
always the org id (see the note in app/services/session_service.py).
"""

from __future__ import annotations

from typing import Any

from google.adk.agents.context import Context
from google.adk.tools.base_tool import BaseTool

from app.models import AgentStatus, CarryingToken
from app.services import store

# Map an ADK tool's name to the "carrying" token shown on the office floor.
# Anything not listed here defaults to CarryingToken.TODO while a tool runs.
_TOOL_CARRY_TOKENS = {
    "read_memory": CarryingToken.FILE,
    "write_memory": CarryingToken.FILE,
    "web_search": CarryingToken.WEB,
    "grep_docs": CarryingToken.GREP,
    "send_message": CarryingToken.MCP,
}


def _ids(context: Context) -> tuple[str, str]:
    """Returns (org_id, agent_id) from the session identifiers."""
    return context.session.user_id, context.session.id


async def before_agent_callback(callback_context: Context):
    # Parameter name is enforced by ADK (not just typed) — see
    # google.adk.agents.base_agent.BaseAgent's before_agent_callback
    # docstring: "MUST be named 'callback_context'". Same story for the
    # other three callbacks below, each against their own enforced name.
    org_id, agent_id = _ids(callback_context)
    store.update_agent_status(org_id, agent_id, AgentStatus.THINKING, action="reasoning")
    return None


async def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: Context):
    org_id, agent_id = _ids(tool_context)
    carrying = _TOOL_CARRY_TOKENS.get(tool.name, CarryingToken.TODO)
    store.update_agent_status(org_id, agent_id, AgentStatus.WORKING, action=f"using {tool.name}", carrying=carrying)
    return None


async def after_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: Context, tool_response: dict[str, Any]):
    org_id, agent_id = _ids(tool_context)
    store.append_trace(org_id, agent_id, f"{tool.name}({args}) -> {tool_response}", kind="tool")
    store.update_agent_status(org_id, agent_id, AgentStatus.WORKING, carrying=CarryingToken.NONE)
    return None


async def after_agent_callback(callback_context: Context):
    org_id, agent_id = _ids(callback_context)
    store.update_agent_status(org_id, agent_id, AgentStatus.IDLE, action="", carrying=CarryingToken.NONE)
    return None
