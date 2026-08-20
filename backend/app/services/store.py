"""Typed CRUD over Firestore for agents/tasks/messages/activity_log.

Built on top of firestore_client.py's org-scoped collection helpers — this
module never imports google.cloud.firestore directly, only the client wrapper.

Firestore field names are camelCase throughout (see the model_config note on
each model in app/models/) since the frontend reads these documents directly
via onSnapshot. Always write through model_dump(by_alias=True) or the
explicit camelCase keys used in update_task/update_agent_status below —
never write a snake_case key directly.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic.alias_generators import to_camel

from app.models import (
    Agent,
    AgentStatus,
    CarryingToken,
    Integration,
    Message,
    Task,
    TaskStatus,
    Trigger,
    Worker,
    WorkerStatus,
)
from app.services.firestore_client import org_collection, org_doc


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- agents ----------------------------------------------------------------


def get_agent(org_id: str, agent_id: str) -> Agent | None:
    snap = org_doc(org_id, "agents", agent_id).get()
    if not snap.exists:
        return None
    return Agent(id=snap.id, **snap.to_dict())


def upsert_agent(org_id: str, agent: Agent) -> None:
    data = agent.model_dump(by_alias=True, exclude={"id"})
    data["updatedAt"] = _now()
    org_doc(org_id, "agents", agent.id).set(data, merge=True)


def list_agents(org_id: str) -> list[Agent]:
    return [Agent(id=d.id, **d.to_dict()) for d in org_collection(org_id, "agents").stream()]


def update_agent_status(
    org_id: str,
    agent_id: str,
    status: AgentStatus,
    action: str | None = None,
    carrying: CarryingToken | None = None,
) -> None:
    update: dict[str, Any] = {"status": status.value, "updatedAt": _now()}
    if action is not None:
        update["action"] = action
    if carrying is not None:
        update["carrying"] = carrying.value
    org_doc(org_id, "agents", agent_id).update(update)


def append_trace(org_id: str, agent_id: str, line: str, kind: str = "tool") -> None:
    org_doc(org_id, "agents", agent_id).collection("trace").add(
        {"ts": _now(), "line": line, "kind": kind}
    )


# ---- per-agent memory (orgs/{orgId}/agents/{agentId}/memory/{memoryId}) ----


def append_memory(org_id: str, agent_id: str, text: str, embedding: list[float], kind: str = "raw") -> str:
    _, doc_ref = org_doc(org_id, "agents", agent_id).collection("memory").add(
        {"text": text, "kind": kind, "embedding": embedding, "createdAt": _now()}
    )
    return doc_ref.id


def list_memory(org_id: str, agent_id: str, limit_count: int = 50) -> list[dict]:
    query = (
        org_doc(org_id, "agents", agent_id)
        .collection("memory")
        .order_by("createdAt", direction="DESCENDING")
        .limit(limit_count)
    )
    return [{"id": d.id, **d.to_dict()} for d in query.stream()]


# ---- tasks -------------------------------------------------------------------


def get_task(org_id: str, task_id: str) -> Task | None:
    snap = org_doc(org_id, "tasks", task_id).get()
    if not snap.exists:
        return None
    return Task(id=snap.id, **snap.to_dict())


def create_task(org_id: str, task: Task) -> None:
    data = task.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "tasks", task.id).set(data)


def update_task(org_id: str, task_id: str, **fields: Any) -> None:
    """Accepts snake_case Python kwargs (matching the Task model's field
    names) and translates them to the camelCase Firestore field names on the
    way out — callers write `has_pending_human_qa=True`, not `hasPendingHumanQa=True`."""
    camel_fields = {to_camel(k): v for k, v in fields.items()}
    camel_fields["updatedAt"] = _now()
    org_doc(org_id, "tasks", task_id).update(camel_fields)


def list_tasks(org_id: str, status: TaskStatus | None = None) -> list[Task]:
    coll = org_collection(org_id, "tasks")
    query = coll.where("status", "==", status.value) if status else coll
    return [Task(id=d.id, **d.to_dict()) for d in query.stream()]


# ---- messages (Firestore mirror of Pub/Sub traffic, for UI/audit reads) ----


def save_message(org_id: str, message: Message) -> None:
    data = message.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "messages", message.id).set(data)


def list_messages(org_id: str, limit: int = 200) -> list[Message]:
    query = org_collection(org_id, "messages").order_by("createdAt", direction="DESCENDING").limit(limit)
    return [Message(id=d.id, **d.to_dict()) for d in query.stream()]


# ---- activity log ------------------------------------------------------------


def log_activity(org_id: str, agent_id: str, event_type: str, message: str, **refs: Any) -> None:
    entry = {"ts": _now(), "agentId": agent_id, "type": event_type, "message": message, **refs}
    org_collection(org_id, "activity_log").add(entry)


# ---- triggers ------------------------------------------------------------


def get_trigger(org_id: str, trigger_id: str) -> Trigger | None:
    snap = org_doc(org_id, "triggers", trigger_id).get()
    if not snap.exists:
        return None
    return Trigger(id=snap.id, **snap.to_dict())


def create_trigger(org_id: str, trigger: Trigger) -> None:
    data = trigger.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "triggers", trigger.id).set(data)


def list_triggers(org_id: str) -> list[Trigger]:
    return [Trigger(id=d.id, **d.to_dict()) for d in org_collection(org_id, "triggers").stream()]


def set_trigger_enabled(org_id: str, trigger_id: str, enabled: bool) -> None:
    org_doc(org_id, "triggers", trigger_id).update({"enabled": enabled})


def mark_trigger_fired(org_id: str, trigger_id: str) -> None:
    org_doc(org_id, "triggers", trigger_id).update({"lastFiredAt": _now()})


def delete_trigger(org_id: str, trigger_id: str) -> None:
    org_doc(org_id, "triggers", trigger_id).delete()


# ---- workers ------------------------------------------------------------


def create_worker(org_id: str, worker: Worker) -> None:
    data = worker.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "workers", worker.id).set(data)


def update_worker(org_id: str, worker_id: str, status: WorkerStatus, result: dict | None = None) -> None:
    update: dict[str, Any] = {"status": status.value, "updatedAt": _now()}
    if result is not None:
        update["result"] = result
    org_doc(org_id, "workers", worker_id).update(update)


def list_workers(org_id: str) -> list[Worker]:
    return [Worker(id=d.id, **d.to_dict()) for d in org_collection(org_id, "workers").stream()]


# ---- integrations ------------------------------------------------------------


def get_integration(org_id: str, integration_id: str) -> Integration | None:
    snap = org_doc(org_id, "integrations", integration_id).get()
    if not snap.exists:
        return None
    return Integration(id=snap.id, **snap.to_dict())


def create_integration(org_id: str, integration: Integration) -> None:
    data = integration.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "integrations", integration.id).set(data)


def list_integrations(org_id: str) -> list[Integration]:
    return [Integration(id=d.id, **d.to_dict()) for d in org_collection(org_id, "integrations").stream()]


def set_integration_enabled(org_id: str, integration_id: str, enabled: bool) -> None:
    org_doc(org_id, "integrations", integration_id).update({"enabled": enabled})


# ---- org membership (defense-in-depth auth, see app/services/auth.py) ------


def add_member(org_id: str, uid: str, role: str = "member") -> None:
    org_doc(org_id, "members", uid).set({"role": role, "addedAt": _now()})


def get_member_role(org_id: str, uid: str) -> str | None:
    snap = org_doc(org_id, "members", uid).get()
    if not snap.exists:
        return None
    return snap.to_dict().get("role", "member")
