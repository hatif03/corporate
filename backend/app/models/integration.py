from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IntegrationAuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    HEADER = "header"
    OAUTH2 = "oauth2"


class Integration(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/integrations/{integrationId}.

    secret_ref points at a Secret Manager resource name — the raw secret
    value is NEVER stored here or anywhere else in Firestore. See
    app/services/integration_broker.py, the only module allowed to
    dereference secret_ref to an actual value.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    kind: str  # "slack", "jira", "github", "stripe", ... — matches an IntegrationTemplate.kind
    base_url: str
    auth_type: IntegrationAuthType
    auth_header: str | None = None  # header name for auth_type=header, e.g. "X-Api-Key"
    secret_ref: str | None = None  # Secret Manager resource name, e.g. "projects/x/secrets/y/versions/latest"
    enabled: bool = True
    connected_departments: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
