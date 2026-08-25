"""Shared helper for running one turn of an ADK agent and getting its final
text response back — used by every department's on_task_received to invoke
its individual pipeline-stage agents. Session id is always the Firestore
agent id that owns the pipeline (e.g. "finance_audit"), so every stage's
lifecycle callbacks update that one agent's status/trace on the office floor,
exactly like a single agent working through several sub-tasks in a row.
"""

from __future__ import annotations

from google.adk.agents.base_agent import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from app.config import settings
from app.services import store


async def run_agent_turn(
    agent: BaseAgent,
    session_service: BaseSessionService,
    org_id: str,
    agent_id: str,
    prompt: str,
) -> str:
    """Sends `prompt` to `agent` as a new user turn in the (org_id, agent_id)
    session and returns the concatenated text of its final response.

    Every agent turn in the app — CEO and every department pipeline stage
    alike — goes through this one function, so it's the single choke point
    for the daily Gemini call budget (ADR-0012). A department turn's
    RuntimeError here is caught by @audited_task's failure path (ADR-0011)
    and surfaced as a blocked task, not a silent failure or a runaway bill.
    """
    if not store.increment_and_check_gemini_budget(org_id, settings.corporate_daily_gemini_call_limit):
        raise RuntimeError("daily Gemini call budget exceeded")

    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="corporate",
        auto_create_session=True,
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text_parts: list[str] = []
    async for event in runner.run_async(user_id=org_id, session_id=agent_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final_text_parts.extend(p.text for p in event.content.parts if p.text)

    return "\n".join(final_text_parts)
