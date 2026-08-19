"""Builds every ADK agent in this project. Nothing outside this module
instantiates LlmAgent/SequentialAgent/ParallelAgent directly — see
.cursor/rules/adk-conventions.mdc.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from app.adk_agents import callbacks
from app.adk_agents.tools.universal import (
    create_task,
    list_agents_tool,
    list_tasks_tool,
    read_memory,
    send_message,
    set_note,
    update_task_status,
    write_board,
    write_memory,
)
from app.config import settings

CEO_SYSTEM_PROMPT = """\
You are the CEO of Corporate, an autonomous company of AI department agents.
Your job is to turn a goal from the human founder into concrete work: decompose
it into tasks, assign each task to the one department best suited for it (by
calling create_task with that department's id as `assignee`), and keep the
company's shared board up to date with anything cross-department that's worth
recording (via write_board).

You are not special-cased in the platform's code — you have the same kind of
reasoning as every department agent, just a different set of tools and a
different job. Departments will reply to you asynchronously with `done` or
`refuse` messages; you do not need to poll for these yourself, they will
appear as new turns.

Use list_agents and list_tasks to check current company state before creating
duplicate work. Keep task descriptions concrete and self-contained — a
department agent only sees what you write in the task, not this conversation.
"""

_CEO_TOOLS = [create_task, write_board, send_message, list_agents_tool, list_tasks_tool, update_task_status]
_DEPARTMENT_UNIVERSAL_TOOLS = [send_message, read_memory, write_memory, set_note]

_UNIVERSAL_CALLBACKS = {
    "before_agent_callback": callbacks.before_agent_callback,
    "before_tool_callback": callbacks.before_tool_callback,
    "after_tool_callback": callbacks.after_tool_callback,
    "after_agent_callback": callbacks.after_agent_callback,
}


def build_ceo_agent() -> LlmAgent:
    return LlmAgent(
        name="ceo",
        model=settings.corporate_gemini_model,
        instruction=CEO_SYSTEM_PROMPT,
        description="CEO orchestrator — decomposes goals into tasks and assigns them to departments.",
        tools=_CEO_TOOLS,
        **_UNIVERSAL_CALLBACKS,
    )


def department_tools(extra_tools: list | None = None) -> list:
    """Every department stage gets the universal tools plus whatever
    department-specific tools it defines in its own tools.py."""
    return [*_DEPARTMENT_UNIVERSAL_TOOLS, *(extra_tools or [])]


def department_callbacks() -> dict:
    """Every department stage attaches the same lifecycle callbacks so its
    status/trace shows up on the office floor identically to the CEO's."""
    return dict(_UNIVERSAL_CALLBACKS)
