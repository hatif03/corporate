"""The only module allowed to import google.cloud.storage directly.

Backs vision attachments (ADR-0013): the backend uploads once, everything
downstream (Task/Message, the Gemini turn itself via types.Part.from_uri)
only ever holds the resulting gs:// URI, never the raw bytes.
"""

from functools import lru_cache
from uuid import uuid4

from google.cloud import storage

from app.config import settings


@lru_cache
def _get_bucket() -> storage.Bucket:
    return storage.Client(project=settings.google_cloud_project).bucket(settings.corporate_attachments_bucket)


def upload_attachment(org_id: str, mime_type: str, data: bytes) -> str:
    """Uploads to gs://{bucket}/orgs/{org_id}/attachments/{uuid}, returns the gs:// URI."""
    blob = _get_bucket().blob(f"orgs/{org_id}/attachments/{uuid4().hex}")
    blob.upload_from_string(data, content_type=mime_type)
    return f"gs://{settings.corporate_attachments_bucket}/{blob.name}"


def upload_public_media(org_id: str, subdir: str, mime_type: str, data: bytes) -> str:
    """Uploads to gs://{bucket}/orgs/{org_id}/{subdir}/{uuid} and makes it
    publicly readable, returning a plain https:// URL a browser can play/
    render directly (unlike upload_attachment's gs:// URI, which only
    Vertex AI itself ever dereferences). Used for generated media that's
    fine to be public by nature (e.g. break-room ambient music, ADR-0019)
    — never for anything containing user data."""
    blob = _get_bucket().blob(f"orgs/{org_id}/{subdir}/{uuid4().hex}")
    blob.upload_from_string(data, content_type=mime_type)
    blob.make_public()
    return blob.public_url
