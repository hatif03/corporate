"""The only module allowed to import google.cloud.storage directly.

Backs vision attachments (ADR-0013): the backend uploads once, everything
downstream (Task/Message, the Gemini turn itself via types.Part.from_uri)
only ever holds the resulting gs:// URI, never the raw bytes.
"""

from datetime import timedelta
from functools import lru_cache
from uuid import uuid4

import google.auth
from google.auth.transport import requests as google_auth_requests
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


def _sign_blob(blob: storage.Blob) -> str:
    """Time-limited signed https:// URL a browser can play/render directly
    — the attachments bucket has Uniform Bucket-Level Access (confirmed
    live), which disables per-object ACLs, so blob.make_public() isn't an
    option. Signing works under UBLA because it's IAM-based, not ACL-based
    — requires corporate-backend-sa to hold roles/iam.serviceAccountTokenCreator
    on ITSELF (self-impersonation, for the IAM Credentials signBlob API
    Cloud Run's ADC needs since there's no private key file here), set up
    once in infra/deploy/setup.sh.

    That grant alone isn't sufficient, reproduced live: generate_signed_url()
    still tries to sign locally with the credential's own private key by
    default, and Compute Engine/Cloud Run credentials (and even a local
    `gcloud auth application-default login` user credential) have none —
    "you need a private key to sign credentials" regardless of the IAM
    grant. The credential has to be handed off explicitly so the signing
    call goes through the IAM Credentials signBlob API instead."""
    credentials, _ = google.auth.default()
    credentials.refresh(google_auth_requests.Request())
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


def upload_playable_media(org_id: str, subdir: str, mime_type: str, data: bytes) -> str:
    """Uploads to gs://{bucket}/orgs/{org_id}/{subdir}/{uuid} and returns a
    signed https:// URL (see _sign_blob) — unlike upload_attachment's gs://
    URI, which only Vertex AI itself ever dereferences. Used for generated
    media a browser needs to fetch directly (e.g. break-room ambient
    music, ADR-0019)."""
    blob = _get_bucket().blob(f"orgs/{org_id}/{subdir}/{uuid4().hex}")
    blob.upload_from_string(data, content_type=mime_type)
    return _sign_blob(blob)


def sign_existing_gcs_uri(gcs_uri: str) -> str:
    """Same signed-URL treatment as upload_playable_media, for a blob Vertex
    AI already wrote directly (Veo's generated video, ADR-0019) rather than
    one this backend uploaded itself — the gs:// URI Veo hands back is only
    dereferenceable by Vertex/gcloud tooling, never by a browser <video>
    tag. Reproduced live: marketing_comms's promo-video task stored the raw
    gs:// URI in task.result.videoUrl, which is why the player showed a
    blank box with nothing playable."""
    if not gcs_uri.startswith(f"gs://{settings.corporate_attachments_bucket}/"):
        raise ValueError(f"expected a gs://{settings.corporate_attachments_bucket}/... URI, got {gcs_uri!r}")
    blob_name = gcs_uri.removeprefix(f"gs://{settings.corporate_attachments_bucket}/")
    return _sign_blob(_get_bucket().blob(blob_name))
