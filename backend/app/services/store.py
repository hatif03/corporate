"""Typed CRUD over Firestore for agents/tasks/messages/activity_log.

Built on top of firestore_client.py's org-scoped collection helpers — this
module never imports google.cloud.firestore directly, only the client wrapper.

Firestore field names are camelCase throughout (see the model_config note on
each model in app/models/) since the frontend reads these documents directly
via onSnapshot. Always write through model_dump(by_alias=True) or the
explicit camelCase keys used in update_task/update_agent_status below —
never write a snake_case key directly.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from google.api_core.exceptions import Conflict
from pydantic.alias_generators import to_camel

from app.models import (
    AccessRequest,
    AccessRequestStatus,
    Agent,
    AgentStatus,
    Attachment,
    CarryingToken,
    Integration,
    KnowledgeDoc,
    Message,
    OrgSettings,
    Task,
    TaskStatus,
    Trigger,
    Worker,
    WorkerStatus,
)
from app.services.firestore_client import increment, org_collection, org_doc


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


def set_agent_paused(org_id: str, agent_id: str, paused: bool) -> None:
    org_doc(org_id, "agents", agent_id).update({"paused": paused, "updatedAt": _now()})


def update_agent_persona(org_id: str, agent_id: str, **fields: Any) -> None:
    """Same snake_case-in, camelCase-out convention as update_org_settings —
    lets an org rename an agent, rewrite its bio, or pick a different sprite
    variant/accent color without touching the department contract itself
    (on_task_received, prompts, ADK pipeline stages are all still real code,
    not editable from here)."""
    camel_fields = {to_camel(k): v for k, v in fields.items()}
    camel_fields["updatedAt"] = _now()
    org_doc(org_id, "agents", agent_id).update(camel_fields)


# ---- per-agent custom skills (orgs/{orgId}/agents/{agentId}/custom_skills) --


def add_agent_custom_skill(org_id: str, agent_id: str, title: str, instructions: str, status: str = "active") -> str:
    """status="active" (default) is the existing human-added-from-Settings
    path — takes effect immediately. status="pending" is an agent's own
    propose_skill tool call (tools/universal.py) — queued for org-owner
    review (approve_agent_custom_skill/delete_agent_custom_skill) before
    with_custom_guidance (shared/custom_skills.py) will ever include it."""
    _, doc_ref = org_doc(org_id, "agents", agent_id).collection("custom_skills").add(
        {"title": title, "instructions": instructions, "status": status, "createdAt": _now()}
    )
    return doc_ref.id


def list_agent_custom_skills(org_id: str, agent_id: str) -> list[dict]:
    query = org_doc(org_id, "agents", agent_id).collection("custom_skills").order_by("createdAt", direction="DESCENDING")
    # status defaults to "active" for skills added before this field existed.
    return [{"id": d.id, "status": "active", **d.to_dict()} for d in query.stream()]


def approve_agent_custom_skill(org_id: str, agent_id: str, skill_id: str) -> None:
    org_doc(org_id, "agents", agent_id).collection("custom_skills").document(skill_id).update({"status": "active"})


def delete_agent_custom_skill(org_id: str, agent_id: str, skill_id: str) -> None:
    org_doc(org_id, "agents", agent_id).collection("custom_skills").document(skill_id).delete()


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


def mark_message_processed(org_id: str, agent_id: str, message_id: str) -> bool:
    """Atomic check-and-set: True the first time this (agent, message) pair
    is seen, False on redelivery. Pub/Sub is at-least-once delivery, so this
    is what makes handle_agent_turn idempotent — see ADR-0011. Uses
    Firestore's native create() (raises Conflict if the doc already exists)
    rather than a read-then-write check, which would race under concurrent
    redelivery."""
    try:
        org_doc(org_id, "processed_messages", f"{agent_id}:{message_id}").create({"processedAt": _now()})
        return True
    except Conflict:
        return False


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


def log_trigger_history(org_id: str, trigger_id: str, payload_preview: str) -> None:
    """orgs/{orgId}/triggers/{id}/history/{firingId} — mirrors the existing
    append_trace/log_activity subcollection pattern. Trigger previously only
    stored a single last-fired timestamp; this is the real log of every
    firing, not just the most recent one."""
    org_doc(org_id, "triggers", trigger_id).collection("history").add(
        {"firedAt": _now(), "payloadPreview": payload_preview[:200]}
    )


def list_trigger_history(org_id: str, trigger_id: str, limit_count: int = 50) -> list[dict]:
    query = (
        org_doc(org_id, "triggers", trigger_id)
        .collection("history")
        .order_by("firedAt", direction="DESCENDING")
        .limit(limit_count)
    )
    return [{"id": d.id, **d.to_dict()} for d in query.stream()]


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


def set_integration_departments(org_id: str, integration_id: str, connected_departments: list[str]) -> None:
    org_doc(org_id, "integrations", integration_id).update({"connectedDepartments": connected_departments})


# ---- knowledge base (orgs/{orgId}/departments/{deptId}/knowledge_base/{id}) --


def append_kb_document(org_id: str, department_id: str, doc: KnowledgeDoc) -> None:
    data = doc.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "departments", department_id).collection("knowledge_base").document(doc.id).set(data)


def list_kb_documents(org_id: str, department_id: str) -> list[KnowledgeDoc]:
    query = (
        org_doc(org_id, "departments", department_id)
        .collection("knowledge_base")
        .order_by("createdAt", direction="DESCENDING")
    )
    return [KnowledgeDoc(id=d.id, **d.to_dict()) for d in query.stream()]


def delete_kb_document(org_id: str, department_id: str, doc_id: str) -> None:
    org_doc(org_id, "departments", department_id).collection("knowledge_base").document(doc_id).delete()


# ---- access requests (orgs/{orgId}/access_requests/{id}) --------------------


def file_access_request(org_id: str, integration_id: str, department_id: str) -> AccessRequest:
    """Files a new pending request, or returns the existing pending one for
    this (integration, department) pair unchanged — repeated denied attempts
    shouldn't spam the owner's queue with duplicates."""
    existing = [
        r
        for r in list_access_requests(org_id)
        if r.integration_id == integration_id and r.department_id == department_id and r.status == AccessRequestStatus.PENDING
    ]
    if existing:
        return existing[0]
    request = AccessRequest(id=f"areq-{uuid.uuid4().hex[:10]}", integration_id=integration_id, department_id=department_id)
    data = request.model_dump(by_alias=True, exclude={"id"})
    org_doc(org_id, "access_requests", request.id).set(data)
    return request


def list_access_requests(org_id: str) -> list[AccessRequest]:
    return [AccessRequest(id=d.id, **d.to_dict()) for d in org_collection(org_id, "access_requests").stream()]


def resolve_access_request(org_id: str, request_id: str, status: AccessRequestStatus, resolved_by: str) -> None:
    org_doc(org_id, "access_requests", request_id).update(
        {"status": status.value, "resolvedAt": _now(), "resolvedBy": resolved_by}
    )


# ---- org membership (defense-in-depth auth, see app/services/auth.py) ------


def add_member(org_id: str, uid: str, role: str = "member") -> None:
    org_doc(org_id, "members", uid).set({"role": role, "addedAt": _now()})


def get_member_role(org_id: str, uid: str) -> str | None:
    snap = org_doc(org_id, "members", uid).get()
    if not snap.exists:
        return None
    return snap.to_dict().get("role", "member")


# ---- Gemini cost guard (ADR-0012) -------------------------------------------


def increment_and_check_gemini_budget(org_id: str, daily_limit: int) -> bool:
    """Increments today's Gemini-call counter (via Firestore's atomic
    Increment, so the write itself can't lose a concurrent increment) and
    returns whether it's still within daily_limit.

    ponytail: the increment is atomic but the follow-up read isn't part of
    the same transaction, so under concurrent calls the read can reflect a
    slightly different count than this call's own increment. Fine for a
    circuit breaker meant to catch gross runaway behavior (hundreds of
    calls), not for exact billing enforcement — upgrade to a Firestore
    transaction if this ever needs to be a hard, race-free cap.
    """
    day_key = _now().strftime("%Y-%m-%d")
    doc_ref = org_doc(org_id, "usage", day_key)
    doc_ref.set({"geminiCalls": increment(1)}, merge=True)
    count = doc_ref.get().to_dict()["geminiCalls"]
    return count <= daily_limit


# ---- per-org settings (ADR-0013) --------------------------------------------


def get_org_settings(org_id: str) -> OrgSettings:
    """Returns all-defaults (unlimited/fallback) OrgSettings when the org
    hasn't configured anything yet — there's no seed step for this doc."""
    snap = org_doc(org_id, "settings", "config").get()
    if not snap.exists:
        return OrgSettings()
    return OrgSettings(**snap.to_dict())


def update_org_settings(org_id: str, **fields: Any) -> None:
    """Same snake_case-in, camelCase-out convention as update_task."""
    camel_fields = {to_camel(k): v for k, v in fields.items()}
    camel_fields["updatedAt"] = _now()
    org_doc(org_id, "settings", "config").set(camel_fields, merge=True)


# ---- vision attachments (ADR-0013) ------------------------------------------


def set_ceo_pending_attachment(org_id: str, attachment: Attachment | None) -> None:
    """Stashes the human's dispatched image on the CEO's own agent doc so
    create_task can pick it up without routing the blob through the LLM's
    tool-call arguments (see app/adk_agents/tools/universal.py)."""
    data = attachment.model_dump(by_alias=True) if attachment else None
    org_doc(org_id, "agents", "ceo").set({"pendingAttachment": data}, merge=True)


def get_ceo_pending_attachment(org_id: str) -> Attachment | None:
    snap = org_doc(org_id, "agents", "ceo").get()
    data = snap.to_dict().get("pendingAttachment") if snap.exists else None
    return Attachment(**data) if data else None
