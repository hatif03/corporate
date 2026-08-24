from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.models.attachment import Attachment


class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    BLOCKED = "blocked"
    DONE = "done"


class HumanQA(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    q: str
    a: str | None = None
    asked_by: str
    answered_at: datetime | None = None
    dismissed_at: datetime | None = None


class Task(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/tasks/{taskId}. camelCase on
    the wire — see the note on Agent in app/models/agent.py."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    title: str
    description: str = ""
    task_type: str
    status: TaskStatus = TaskStatus.TODO
    assignee: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    human_qa: list[HumanQA] = Field(default_factory=list)
    has_pending_human_qa: bool = False
    result: dict[str, Any] | None = None
    created_by: str
    priority: int = 3
    # Which Gemini tier this task's turn(s) run on — set by the CEO's
    # create_task call, see ADR-0013.
    model_tier: Literal["flash", "pro"] = "flash"
    attachment: Attachment | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
