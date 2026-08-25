"""Builds every ADK agent in this project. Nothing outside this module
instantiates LlmAgent/SequentialAgent/ParallelAgent directly — see
.cursor/rules/adk-conventions.mdc.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.google_search_agent_tool import create_google_search_agent, GoogleSearchAgentTool

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

# The raw google_search built-in tool can't be combined with custom function
# tools on the same agent — GoogleSearchAgentTool is ADK's own documented
# workaround: a search-only sub-agent wrapped as a regular AgentTool, so it
# drops into _CEO_TOOLS/_DEPARTMENT_UNIVERSAL_TOOLS like any other tool.
# Always runs on flash regardless of the parent turn's tier (see
# build_tiered_stage_agents below) — its job is "call google_search, return
# results," not reasoning.
_google_search_sub_agent = create_google_search_agent(model=settings.corporate_gemini_model)
google_search_tool = GoogleSearchAgentTool(agent=_google_search_sub_agent)

_CEO_TOOLS = [
    create_task, write_board, send_message, list_agents_tool, list_tasks_tool, update_task_status, google_search_tool,
]
_DEPARTMENT_UNIVERSAL_TOOLS = [send_message, read_memory, write_memory, set_note, google_search_tool]

_UNIVERSAL_CALLBACKS = {
    "before_agent_callback": callbacks.before_agent_callback,
    "before_tool_callback": callbacks.before_tool_callback,
    "after_tool_callback": callbacks.after_tool_callback,
    "after_agent_callback": callbacks.after_agent_callback,
}

# One LlmAgent per Gemini tier — a department's create_task-time model_tier
# choice (ADR-0013) picks which singleton to run a turn on. Agents are
# module-level singletons built once at import time (see departments/*), so
# mutating a shared singleton's .model per-turn would race across concurrent
# orgs on Cloud Run; two pre-built singletons sidesteps that entirely.
_MODEL_BY_TIER = {"flash": settings.corporate_gemini_model, "pro": settings.corporate_gemini_model_pro}


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


def build_tiered_stage_agents(
    name: str, instruction: str, description: str, extra_tools: list | None = None
) -> dict[str, LlmAgent]:
    """One LlmAgent singleton per Gemini tier for a single pipeline stage,
    sharing instruction/tools/callbacks — a department's on_task_received
    picks agents_by_tier[task.model_tier] instead of mutating a shared
    singleton's .model at runtime. See ADR-0013."""
    return {
        tier: LlmAgent(
            name=f"{name}_{tier}",
            model=model,
            instruction=instruction,
            description=description,
            tools=department_tools(extra_tools),
            **department_callbacks(),
        )
        for tier, model in _MODEL_BY_TIER.items()
    }
