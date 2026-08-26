"""Trigger CRUD, the webhook receiver, and the Cloud-Scheduler-facing 'fire'
endpoint. See docs/system_prompt.md's Triggers section and
/infra/deploy/ for the `gcloud scheduler jobs create http` command that
targets /internal/triggers/{org_id}/{trigger_id}/fire."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.models import Act, Trigger, TriggerType
from app.services import pubsub_client, store
from app.services.workers import spawn_worker

router = APIRouter(prefix="/api/org/{org_id}/triggers", tags=["triggers"])
# org_id is explicit in the path (not just a query param) since every
# schedule trigger belongs to exactly one org and the Cloud Scheduler job
# created for it (see /infra/deploy/ and README.md) bakes the full URL in.
internal_router = APIRouter(prefix="/internal/triggers/{org_id}", tags=["triggers-internal"])


class CreateTriggerRequest(BaseModel):
    name: str
    type: TriggerType
    target_agent: str
    payload_template: str
    cron: str | None = None


@router.post("")
async def create_trigger(org_id: str, body: CreateTriggerRequest) -> dict:
    if body.type == TriggerType.SCHEDULE and not body.cron:
        raise HTTPException(status_code=400, detail="schedule triggers require a cron expression")

    trigger = Trigger(
        id=f"trig-{uuid.uuid4().hex[:10]}",
        name=body.name,
        type=body.type,
        target_agent=body.target_agent,
        payload_template=body.payload_template,
        cron=body.cron,
        webhook_secret=secrets.token_hex(16) if body.type == TriggerType.WEBHOOK else None,
    )
    store.create_trigger(org_id, trigger)
    return trigger.model_dump(mode="json", by_alias=True)


@router.post("/{trigger_id}/toggle")
async def toggle_trigger(org_id: str, trigger_id: str, enabled: bool) -> dict:
    store.set_trigger_enabled(org_id, trigger_id, enabled)
    return {"enabled": enabled}


@router.delete("/{trigger_id}")
async def delete_trigger(org_id: str, trigger_id: str) -> dict:
    store.delete_trigger(org_id, trigger_id)
    return {"deleted": True}


@router.get("/{trigger_id}/history")
async def trigger_history(org_id: str, trigger_id: str) -> list[dict]:
    return store.list_trigger_history(org_id, trigger_id)


@router.post("/{trigger_id}/webhook")
async def receive_webhook(org_id: str, trigger_id: str, request: Request) -> dict:
    trigger = store.get_trigger(org_id, trigger_id)
    if trigger is None or trigger.type != TriggerType.WEBHOOK:
        raise HTTPException(status_code=404, detail="no such webhook trigger")
    if not trigger.enabled:
        raise HTTPException(status_code=403, detail="trigger is disabled")

    provided_secret = request.headers.get("X-Trigger-Secret")
    if provided_secret != trigger.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    body = await request.body()
    _fire_trigger(org_id, trigger, body.decode("utf-8", errors="replace"))
    return {"fired": True}


@internal_router.post("/{trigger_id}/fire")
async def fire_scheduled_trigger(org_id: str, trigger_id: str) -> dict:
    """Target of the Cloud Scheduler job created for a schedule-type trigger."""
    trigger = store.get_trigger(org_id, trigger_id)
    if trigger is None or trigger.type != TriggerType.SCHEDULE:
        raise HTTPException(status_code=404, detail="no such schedule trigger")
    if not trigger.enabled:
        return {"fired": False, "reason": "disabled"}

    _fire_trigger(org_id, trigger, "")
    return {"fired": True}


def _fire_trigger(org_id: str, trigger: Trigger, payload_text: str) -> None:
    # A plain substring replace, not str.format() — payload_template may
    # legitimately contain other literal braces (e.g. a JSON example) that
    # .format() would misparse as format fields.
    rendered_body = trigger.payload_template.replace("{payload}", payload_text)

    if trigger.target_agent == "worker":
        spawn_worker(org_id, source_event=f"trigger:{trigger.id}", prompt=rendered_body)
    else:
        pubsub_client.publish_message(
            org_id=org_id,
            from_agent="trigger",
            to=trigger.target_agent,
            act=Act.REQUEST,
            subject=f"Trigger: {trigger.name}",
            body=rendered_body,
        )
    store.mark_trigger_fired(org_id, trigger.id)
    store.log_trigger_history(org_id, trigger.id, payload_text or rendered_body)
