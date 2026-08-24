from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class OrgSettings(BaseModel):
    """Mirrors Firestore doc at orgs/{orgId}/settings/config. See ADR-0013."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    daily_gemini_call_limit: int | None = None  # None = use settings.corporate_daily_gemini_call_limit
    updated_at: datetime | None = None
