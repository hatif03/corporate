from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Attachment(BaseModel):
    """A vision attachment already uploaded to Cloud Storage (see
    app/services/storage_client.py) — only ever holds a reference, never raw
    bytes, so it's safe to store directly on a Task/Message doc."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mime_type: str
    gcs_uri: str
