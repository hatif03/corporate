from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TriggerType(str, Enum):
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"


class Trigger(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/triggers/{triggerId}."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    type: TriggerType
    target_agent: str
    payload_template: str
    cron: str | None = None  # required for type=schedule (Cloud Scheduler expression)
    webhook_secret: str | None = None  # required for type=webhook
    enabled: bool = True
    last_fired_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerStatus(str, Enum):
    SPAWNED = "spawned"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Worker(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/workers/{workerId}.

    ponytail: workers run as in-process asyncio tasks (app/services/workers.py),
    not real Cloud Run Job executions — cloudRunJobExecutionId stays null
    until this is deployed and that upgrade is made. See that module's
    docstring for the upgrade path.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    source_event: str
    status: WorkerStatus = WorkerStatus.SPAWNED
    agent_id: str
    conversation: str
    cloud_run_job_execution_id: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
