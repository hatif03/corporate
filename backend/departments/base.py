"""The DepartmentSpec contract every department implements.

See docs/adr/0005-department-contract-and-scaffolding.md. `on_task_received`
is the ONLY entrypoint the platform calls — it is wrapped by @audited_task,
which handles hash-chained audit logging and the task-status/reply writeback
so individual departments don't have to.

Departments are stateless modules (their LlmAgents and session service are
module-level singletons, not instance state), so on_task_received is a plain
function of (org_id, task) -> TaskResult, not a bound method — there is no
department "instance" to hold `self`.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from google.adk.agents.base_agent import BaseAgent

from app.models import Act, HumanQA, Task, TaskResult, TaskStatus
from app.services import pubsub_client, store
from shared import audit_chain

OnTaskReceived = Callable[[str, Task], Awaitable[TaskResult]]


@dataclass
class DepartmentSpec:
    department_id: str
    display_name: str
    description: str
    accepted_task_types: list[str]
    memory_namespace: str
    on_task_received: OnTaskReceived
    root_agent: BaseAgent | None = None
    aspects: dict[str, Callable] = field(default_factory=dict)
    requires_human_review: Callable[[TaskResult], bool] | None = None
    a2a_exposed: bool = False
    # root_agent is populated when a department's pipeline is a single,
    # directly-invokable ADK agent tree (needed for A2A exposure via
    # to_a2a(), see ADR-0004) — it is NOT how the platform dispatches work,
    # that's always on_task_received. A department whose pipeline mixes
    # deterministic Python steps between LLM calls (e.g. finance_audit's
    # isolated fraud stage, ADR-0006) may leave this None and orchestrate
    # its stage agents directly in on_task_received instead.


def _ask_human(org_id: str, task: Task, question: str, department_id: str) -> None:
    """Append a real HumanQA entry to the task and mark it BLOCKED pending an
    answer — used both when a department deliberately asks for human input
    and when it fails outright (see ADR-0011). Without this, has_pending_human_qa
    was true but task.human_qa stayed empty, so POST /tasks/{id}/answer had
    nothing to index into."""
    qa_list = [*task.human_qa, HumanQA(q=question, asked_by=department_id)]
    store.update_task(
        org_id,
        task.id,
        status=TaskStatus.BLOCKED.value,
        has_pending_human_qa=True,
        human_qa=[qa.model_dump(by_alias=True, mode="json") for qa in qa_list],
    )


def audited_task(department_id: str) -> Callable[[OnTaskReceived], OnTaskReceived]:
    """Wraps a department's on_task_received: appends a tamper-evident audit
    entry, updates the task's Firestore status, and sends the reply message
    back to the requester. Departments never call audit_chain or
    pubsub_client.publish_message directly for this — this decorator is the
    only place that does.

    Also the only place that catches a department's failure (ADR-0011): a
    department raising — a Gemini timeout, malformed LLM JSON, whatever —
    never propagates to a bare 500 (which would leave the task stuck at
    DOING forever and tell Pub/Sub to retry indefinitely). It's caught,
    audited as a failure, surfaced to a human via the same Ask-me path as a
    deliberate needs_human result, and the requester gets a real reply
    instead of silence."""

    def decorator(fn: OnTaskReceived) -> OnTaskReceived:
        @functools.wraps(fn)
        async def wrapper(org_id: str, task: Task) -> TaskResult:
            store.update_task(org_id, task.id, status=TaskStatus.DOING.value)

            try:
                result = await fn(org_id, task)
            except Exception as exc:  # noqa: BLE001 - a department failure must never crash the dispatch path
                audit_chain.append_entry(
                    org_id=org_id,
                    department_id=department_id,
                    task_id=task.id,
                    actor=department_id,
                    action="on_task_received_failed",
                    payload={"error": str(exc)},
                )
                store.log_activity(org_id, department_id, "task-failed", f"task {task.id} failed: {exc}")
                _ask_human(org_id, task, f"This task failed to process: {exc}. Needs human review.", department_id)
                pubsub_client.publish_message(
                    org_id=org_id,
                    from_agent=department_id,
                    to=task.created_by,
                    act=Act.REFUSE,
                    subject=f"Re: {task.title}",
                    body=f"Failed: {exc}",
                    needs_human=True,
                )
                return TaskResult(success=False, summary=f"Failed: {exc}", needs_human=True)

            audit_chain.append_entry(
                org_id=org_id,
                department_id=department_id,
                task_id=task.id,
                actor=department_id,
                action="on_task_received",
                payload={"success": result.success, "summary": result.summary},
            )

            if result.needs_human:
                _ask_human(org_id, task, result.human_question or result.summary, department_id)
            elif not result.success:
                # A department can legitimately decline/fail a task without
                # explicitly asking a question (result.needs_human=False) —
                # still route it through _ask_human so the reason is never
                # silently lost: the Tasks UI has nowhere else to show
                # `result.summary`, and a BLOCKED task with no human_qa entry
                # is indistinguishable from one that never explained itself.
                _ask_human(org_id, task, result.summary, department_id)
            else:
                store.update_task(
                    org_id,
                    task.id,
                    status=TaskStatus.DONE.value,
                    result=result.data or {},
                )

            requester = task.created_by
            pubsub_client.publish_message(
                org_id=org_id,
                from_agent=department_id,
                to=requester,
                act=Act.DONE if result.success else Act.REFUSE,
                subject=f"Re: {task.title}",
                body=result.summary,
                needs_human=result.needs_human,
            )
            return result

        return wrapper

    return decorator
