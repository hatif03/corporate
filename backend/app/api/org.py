"""Human-facing mutation endpoints. Reads (agent roster, kanban, activity,
messages) go straight from the frontend to Firestore via onSnapshot — this
router is only for actions a human takes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.models import Act, HumanQA
from app.services import pubsub_client, store

router = APIRouter(prefix="/api/org/{org_id}", tags=["org"])


class DispatchRequest(BaseModel):
    text: str


@router.post("/dispatch")
async def dispatch(org_id: str, body: DispatchRequest) -> dict:
    """The Monitor tab's 'dispatch a task' box: a human sends a goal straight
    to the CEO, who decomposes it into department tasks."""
    message = pubsub_client.publish_message(
        org_id=org_id,
        from_agent="human",
        to="ceo",
        act=Act.REQUEST,
        subject="New goal from founder",
        body=body.text,
    )
    return {"message_id": message.id}


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
