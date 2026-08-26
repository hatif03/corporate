from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AccessRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class AccessRequest(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/access_requests/{requestId} —
    filed by call_integration (app/services/integration_broker.py) when a
    department without access attempts a configured integration. A
    standing, owner-resolved queue, not a task-blocking flow — see
    docs/system_prompt.md's Integrations section."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    integration_id: str
    department_id: str
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolved_by: str | None = None
