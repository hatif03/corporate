from typing import Any

from pydantic import BaseModel


class TaskResult(BaseModel):
    """What a department's on_task_received returns. The base class turns this
    into a task status update plus a reply Message back to the requester."""

    success: bool
    summary: str
    data: dict[str, Any] | None = None
    needs_human: bool = False
    human_question: str | None = None
