from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    SUCCESS = "success"
    GHOST = "ghost"
    COMPACTING = "compacting"
    LOOPING = "looping"
    TYPING = "typing"


class CarryingToken(str, Enum):
    NONE = "none"
    FILE = "file"
    BASH = "bash"
    WEB = "web"
    GREP = "grep"
    MCP = "mcp"
    TODO = "todo"


class Agent(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/agents/{agentId}.

    Field names serialize to camelCase (Firestore/frontend convention — the
    frontend reads these documents directly via onSnapshot, so the on-disk
    field names ARE the frontend contract). Always write with
    model_dump(by_alias=True); reading works either way since
    populate_by_name=True accepts both forms.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    character: str = "default"
    avatar_sprite_id: str = "default"
    department: str
    accent_color: str = "sky"
    description: str = ""
    goal: str | None = None
    note: str | None = None
    status: AgentStatus = AgentStatus.IDLE
    action: str = ""
    progress: float = 0.0
    current_station: str | None = None
    carrying: CarryingToken = CarryingToken.NONE
    is_ceo: bool = False
    provider: str = "adk"
    model: str = ""
    adk_session_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
