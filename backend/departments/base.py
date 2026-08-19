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

from app.models import Act, Task, TaskResult, TaskStatus
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


def audited_task(department_id: str) -> Callable[[OnTaskReceived], OnTaskReceived]:
    """Wraps a department's on_task_received: appends a tamper-evident audit
    entry, updates the task's Firestore status, and sends the reply message
    back to the requester. Departments never call audit_chain or
    pubsub_client.publish_message directly for this — this decorator is the
    only place that does."""

    def decorator(fn: OnTaskReceived) -> OnTaskReceived:
        @functools.wraps(fn)
        async def wrapper(org_id: str, task: Task) -> TaskResult:
            store.update_task(org_id, task.id, status=TaskStatus.DOING.value)
            result = await fn(org_id, task)

            audit_chain.append_entry(
                org_id=org_id,
                department_id=department_id,
                task_id=task.id,
                actor=department_id,
                action="on_task_received",
                payload={"success": result.success, "summary": result.summary},
            )

            if result.needs_human:
                store.update_task(
                    org_id,
                    task.id,
                    status=TaskStatus.BLOCKED.value,
                    has_pending_human_qa=True,
                )
            else:
                store.update_task(
                    org_id,
                    task.id,
                    status=TaskStatus.DONE.value if result.success else TaskStatus.BLOCKED.value,
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
