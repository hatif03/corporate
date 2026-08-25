"""Turns one inbound Message into either a department's on_task_received
call or a CEO agent turn. This is the one handler both the real Pub/Sub push
endpoint (app/api/internal.py) and the LOCAL_DEV pull loop
(app/services/pubsub_local.py) call — see docs/system_prompt.md's note that
push/pull must share the same handler function.
"""

from __future__ import annotations

from app.adk_agents.factory import build_ceo_agent
from app.adk_agents.runtime import run_agent_turn
from app.models import Act, Message
from app.services import store
from app.services.session_service import FirestoreSessionService
from departments import get_department

_session_service = FirestoreSessionService()
_ceo_agent = build_ceo_agent()


async def handle_agent_turn(org_id: str, agent_id: str, message: Message) -> None:
    # Pub/Sub is at-least-once delivery; this is the single dedupe point
    # both the real push endpoint and the LOCAL_DEV pull loop share (see
    # ADR-0011) — a redelivered message is a silent no-op, not a re-run.
    if not store.mark_message_processed(org_id, agent_id, message.id):
        store.log_activity(org_id, agent_id, "duplicate-skipped", f"message {message.id} already processed")
        return

    # Departments' own failures are already caught and surfaced by
    # @audited_task (see departments/base.py, ADR-0011) — this try/except is
    # the last-resort net for everything else (get_department/store.get_task
    # raising, or the CEO-turn branch below, which doesn't go through
    # audited_task at all). Never let anything here propagate: an unhandled
    # exception here is a bare 500 from the push endpoint, which tells
    # Pub/Sub to retry the same message forever.
    try:
        department = get_department(agent_id)

        if department is not None and message.act == Act.REQUEST:
            task = store.get_task(org_id, message.conversation)
            if task is None:
                store.log_activity(
                    org_id, agent_id, "dispatch-error", f"no task found for conversation {message.conversation}"
                )
                return
            await department.on_task_received(org_id, task)
            return

        if agent_id == "ceo":
            prompt = f"Message from {message.from_} ({message.act.value}) — {message.subject}: {message.body}"
            await run_agent_turn(_ceo_agent, _session_service, org_id, "ceo", prompt)
            return

        store.log_activity(
            org_id, agent_id, "dispatch-unhandled", f"no handler for act={message.act.value} on agent {agent_id}"
        )
    except Exception as exc:  # noqa: BLE001 - see the docstring above this try
        store.log_activity(org_id, agent_id, "dispatch-failed", f"unhandled error dispatching {message.id}: {exc}")
