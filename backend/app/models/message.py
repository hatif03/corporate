from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Act(str, Enum):
    """Speech-act types. request/query/propose obligate a reply; inform/agree/refuse/done are terminal."""

    REQUEST = "request"
    INFORM = "inform"
    PROPOSE = "propose"
    QUERY = "query"
    AGREE = "agree"
    REFUSE = "refuse"
    DONE = "done"


REPLY_OBLIGATING_ACTS = {Act.REQUEST, Act.QUERY, Act.PROPOSE}


class Message(BaseModel):
    """FIPA-lite inter-agent message. Mirrors both the Pub/Sub payload and the
    Firestore orgs/{orgId}/messages/{messageId} document. camelCase on the
    wire except `from`/`to`, which stay as documented in the message schema
    (docs/system_prompt.md) since `from` is a Python keyword and needs its
    own explicit alias regardless of the generator."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    conversation: str
    in_reply_to: str | None = None
    from_: str = Field(alias="from")
    to: str
    act: Act
    subject: str
    body: str
    hops: int = 0
    requires_reply: bool
    needs_human: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None
    processed_at: datetime | None = None
    pubsub_message_id: str | None = None
