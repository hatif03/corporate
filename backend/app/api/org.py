"""Human-facing mutation endpoints. Reads (agent roster, kanban, activity,
messages) go straight from the frontend to Firestore via onSnapshot — this
router is only for actions a human takes."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import Act, Attachment, HumanQA
from app.services import pubsub_client, storage_client, store

router = APIRouter(prefix="/api/org/{org_id}", tags=["org"])

# ~700KB before base64's ~33% inflation, well under Cloud Run's 32MB request
# body limit — this is a demo image size guard, not a load-bearing one.
_MAX_ATTACHMENT_B64_CHARS = 30_000_000


class DispatchRequest(BaseModel):
    text: str
    attachment_data_b64: str | None = None
    attachment_mime_type: str | None = None


@router.post("/dispatch")
async def dispatch(org_id: str, body: DispatchRequest) -> dict:
    """The Monitor tab's 'dispatch a task' box: a human sends a goal straight
    to the CEO, who decomposes it into department tasks. An optional image
    is uploaded to Cloud Storage here (see ADR-0013) — only the resulting
    gs:// reference travels any further, never the raw bytes."""
    attachment: Attachment | None = None
    if body.attachment_data_b64:
        if not body.attachment_mime_type:
            raise HTTPException(status_code=400, detail="attachment_mime_type is required with attachment_data_b64")
        if len(body.attachment_data_b64) > _MAX_ATTACHMENT_B64_CHARS:
            raise HTTPException(status_code=400, detail="attachment too large")
        data = base64.b64decode(body.attachment_data_b64)
        gcs_uri = storage_client.upload_attachment(org_id, body.attachment_mime_type, data)
        attachment = Attachment(mime_type=body.attachment_mime_type, gcs_uri=gcs_uri)

    message = pubsub_client.publish_message(
        org_id=org_id,
        from_agent="human",
        to="ceo",
        act=Act.REQUEST,
        subject="New goal from founder",
        body=body.text,
        attachment=attachment,
    )
    return {"message_id": message.id}


@router.get("/settings")
async def get_settings(org_id: str) -> dict:
    return store.get_org_settings(org_id).model_dump(mode="json", by_alias=True)


class UpdateSettingsRequest(BaseModel):
    daily_gemini_call_limit: int | None = None


@router.post("/settings")
async def update_settings(org_id: str, body: UpdateSettingsRequest) -> dict:
    if body.daily_gemini_call_limit is not None and body.daily_gemini_call_limit < 1:
        raise HTTPException(status_code=400, detail="daily_gemini_call_limit must be >= 1 or omitted for unlimited")
    store.update_org_settings(org_id, daily_gemini_call_limit=body.daily_gemini_call_limit)
    return store.get_org_settings(org_id).model_dump(mode="json", by_alias=True)


class AnswerRequest(BaseModel):
    answer: str
    question_index: int = 0


@router.post("/tasks/{task_id}/answer")
async def answer_question(org_id: str, task_id: str, body: AnswerRequest) -> dict:
    """Ask-me tab: a human answers a task's pending human_qa entry."""
    task = store.get_task(org_id, task_id)
    if task is None:
        return {"error": "task not found"}

    qa_list = task.human_qa
    if body.question_index >= len(qa_list):
        return {"error": "no such question"}

    qa_list[body.question_index] = HumanQA(
        q=qa_list[body.question_index].q,
        a=body.answer,
        asked_by=qa_list[body.question_index].asked_by,
        answered_at=datetime.now(timezone.utc),
    )
    still_pending = any(qa.a is None for qa in qa_list)
    store.update_task(
        org_id,
        task_id,
        human_qa=[qa.model_dump(by_alias=True, mode="json") for qa in qa_list],
        has_pending_human_qa=still_pending,
    )

    pubsub_client.publish_message(
        org_id=org_id,
        from_agent="human",
        to=task.assignee or "ceo",
        act=Act.INFORM,
        subject=f"Re: {task.title}",
        body=body.answer,
        conversation=task_id,
    )
    return {"answered": True}
