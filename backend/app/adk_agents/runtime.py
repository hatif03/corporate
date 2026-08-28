"""Shared helper for running one turn of an ADK agent and getting its final
text response back — used by every department's on_task_received to invoke
its individual pipeline-stage agents. Session id is always the Firestore
agent id that owns the pipeline (e.g. "finance_audit"), so every stage's
lifecycle callbacks update that one agent's status/trace on the office floor,
exactly like a single agent working through several sub-tasks in a row.
"""

from __future__ import annotations

import json

from google.adk.agents.base_agent import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from app.config import settings
from app.models import Attachment
from app.services import store
from app.services.memory_search import search_memory

MEMORY_AUTO_SURFACE_TOP_K = 6  # widened so an agent's own past notes stay useful as memory grows (paired with the periodic memory-curation trigger, scripts/seed.py)

MAX_TOOL_CALLS_PER_TURN = 25  # a runaway-loop backstop, not a tight budget
MAX_IDENTICAL_REPEATS = 3  # in a row, not total — matches opencode's own
# doom-loop constant (packages/opencode/src/tool/processor.ts, MIT,
# anomalyco/opencode — see /THIRD_PARTY_SKILLS.md). opencode pauses for a
# human permission prompt before the 4th identical repeat; this backend has
# no synchronous human-in-the-loop gate mid-turn, so it raises instead —
# @audited_task (ADR-0011) turns that into a BLOCKED task + HumanQA entry,
# the async equivalent of "stop and ask a human."


def _relevant_memory_block(org_id: str, agent_id: str, prompt: str) -> str | None:
    """Gated auto-surfacing: a cheap existence check (no embedding call)
    first, so an agent with no memory yet — the common case early in an
    org's life — costs nothing extra on this, the hottest code path in the
    app. Only agents that actually have memory pay for a real semantic
    search. Separate from (and complements) search_memory_tool, which lets
    an agent explicitly search for something specific on demand."""
    if not store.list_memory(org_id, agent_id, limit_count=1):
        return None
    hits = search_memory(org_id, prompt, agent_id=agent_id, top_k=MEMORY_AUTO_SURFACE_TOP_K)
    if not hits:
        return None
    lines = "\n".join(f"- {h.text}" for h in hits)
    return f"Relevant memory from your own past notes:\n{lines}"


async def run_agent_turn(
    agent: BaseAgent,
    session_service: BaseSessionService,
    org_id: str,
    agent_id: str,
    prompt: str,
    attachment: Attachment | None = None,
) -> str:
    """Sends `prompt` to `agent` as a new user turn in the (org_id, agent_id)
    session and returns the concatenated text of its final response.

    Every agent turn in the app — CEO and every department pipeline stage
    alike — goes through this one function, so it's the single choke point
    for the daily Gemini call budget (ADR-0012/0013). A department turn's
    RuntimeError here is caught by @audited_task's failure path (ADR-0011)
    and surfaced as a blocked task, not a silent failure or a runaway bill.
    """
    effective_limit = store.get_org_settings(org_id).daily_gemini_call_limit or settings.corporate_daily_gemini_call_limit
    if not store.increment_and_check_gemini_budget(org_id, effective_limit):
        raise RuntimeError("daily Gemini call budget exceeded")

    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="corporate",
        auto_create_session=True,
    )
    memory_block = _relevant_memory_block(org_id, agent_id, prompt)
    effective_prompt = f"{memory_block}\n\n{prompt}" if memory_block else prompt
    parts = [types.Part(text=effective_prompt)]
    if attachment:
        # Vertex AI reads the gs:// object directly — no download/re-encode
        # needed here. See ADR-0013.
        parts.append(types.Part.from_uri(file_uri=attachment.gcs_uri, mime_type=attachment.mime_type))
    message = types.Content(role="user", parts=parts)

    final_text_parts: list[str] = []
    tool_call_count = 0
    last_call_key: str | None = None
    repeat_streak = 0
    async for event in runner.run_async(user_id=org_id, session_id=agent_id, new_message=message):
        for fc in event.get_function_calls():
            tool_call_count += 1
            if tool_call_count > MAX_TOOL_CALLS_PER_TURN:
                raise RuntimeError(f"turn exceeded {MAX_TOOL_CALLS_PER_TURN} tool calls without finishing")
            key = f"{fc.name}:{json.dumps(fc.args, sort_keys=True, default=str)}"
            repeat_streak = repeat_streak + 1 if key == last_call_key else 1
            last_call_key = key
            if repeat_streak >= MAX_IDENTICAL_REPEATS:
                raise RuntimeError(
                    f"stuck loop: {fc.name} called with identical arguments {MAX_IDENTICAL_REPEATS} times in a row"
                )
        if event.is_final_response() and event.content and event.content.parts:
            final_text_parts.extend(p.text for p in event.content.parts if p.text)

    return "\n".join(final_text_parts)
