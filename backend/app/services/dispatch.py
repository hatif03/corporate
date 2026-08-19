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
