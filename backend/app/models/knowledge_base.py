from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class KnowledgeDoc(BaseModel):
    """Mirrors Firestore doc at
    orgs/{orgId}/departments/{departmentId}/knowledge_base/{docId} — an
    org-uploaded document that supplements (or, once any exist, replaces)
    a department's static embedded corpus. See
    app/services/knowledge_base.py's department_kb_text()."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    title: str
    text: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
