"""Ephemeral, single-job agents: "run to completion, reply, then tear down"
— e.g. a Slack DM to the company that doesn't map to any existing task.

ponytail: this runs the worker as an in-process asyncio task, not a real
Cloud Run Job execution (cloudRunJobExecutionId on the Worker model stays
null). That's the correct MVP shape given no live Cloud Run deployment
exists yet to spawn jobs on. Upgrade path once deployed: replace
asyncio.create_task(_run_worker(...)) with a
`gcloud run jobs execute corporate-worker --args=...` call (or the
equivalent Cloud Run Jobs API call), and have that job process call back
into update_worker() on completion instead of doing it in-process.
"""

from __future__ import annotations

import asyncio
import uuid

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Worker, WorkerStatus
from app.services import store
from app.services.session_service import FirestoreSessionService

WORKER_INSTRUCTION = """\
You are an ephemeral one-off worker for Corporate. You've been spawned to
handle a single inbound event (e.g. a Slack message) that doesn't map to an
existing task. Read it, respond helpfully and concisely, and if it clearly
belongs to a specific department, use send_message to hand it to that
department (act=inform) rather than trying to solve it yourself.
"""

# Two module-level singletons (flash/pro), same reason as every department's
# build_tiered_stage_agents call: ADK agents are module-level singletons
# built once at import time, so a per-call model swap isn't safe across
# concurrent orgs — see ADR-0013.
_worker_agents = build_tiered_stage_agents(
    "worker_generic", instruction=WORKER_INSTRUCTION,
    description="Ephemeral one-off worker for inbound events with no existing task",
)

_session_service = FirestoreSessionService()

# Handles for running workers, keyed by worker_id, so a human can stop one
# from the Workers tab. Cleared once a worker finishes either way.
_running_tasks: dict[str, asyncio.Task] = {}


def stop_worker(org_id: str, worker_id: str) -> bool:
    task = _running_tasks.get(worker_id)
    if task is None or task.done():
        return False
    task.cancel()
    store.update_worker(org_id, worker_id, WorkerStatus.FAILED, result={"error": "stopped by user"})
    return True


async def _run_worker(org_id: str, worker_id: str, conversation: str, prompt: str, model_tier: str) -> None:
    store.update_worker(org_id, worker_id, WorkerStatus.RUNNING)
    try:
        # Each worker gets its own session id so it doesn't share state with
        # any registered department agent — a real "spin up, do one thing,
        # tear down" identity.
        reply = await run_agent_turn(_worker_agents[model_tier], _session_service, org_id, worker_id, prompt)
        store.update_worker(org_id, worker_id, WorkerStatus.DONE, result={"reply": reply})
    except Exception as exc:  # noqa: BLE001 - worker failures must not crash the caller
        store.update_worker(org_id, worker_id, WorkerStatus.FAILED, result={"error": str(exc)})
    finally:
        _running_tasks.pop(worker_id, None)


def spawn_worker(
    org_id: str, source_event: str, prompt: str, target_agent: str | None = None, model_tier: str = "flash"
) -> str:
    """Fire off a new worker and return its id immediately — the caller
    (e.g. a Slack webhook handler) doesn't block on the worker finishing.

    target_agent is a soft hint folded into the prompt, not a hard routing
    change — the worker agent already has send_message and instructions to
    hand off to the right department when appropriate; naming a department
    up front just gives it a strong hint instead of making it guess."""
    worker_id = f"worker-{uuid.uuid4().hex[:10]}"
    conversation = f"worker-conv-{uuid.uuid4().hex[:8]}"
    store.create_worker(
        org_id,
        Worker(id=worker_id, source_event=source_event, agent_id=worker_id, conversation=conversation),
    )
    full_prompt = f"(Likely belongs to: {target_agent})\n{prompt}" if target_agent else prompt
    task = asyncio.create_task(_run_worker(org_id, worker_id, conversation, full_prompt, model_tier))
    _running_tasks[worker_id] = task
    return worker_id
