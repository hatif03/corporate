"""Marketing promo-video generation via Vertex AI's Veo model (ADR-0019).

Veo generation is a genuinely slow, asynchronous operation (minutes, not
seconds) — this module only ever KICKS OFF an operation
(start_video_generation) or CHECKS one that's already running
(check_video_generation). Nothing here blocks waiting for completion: a
Pub/Sub push handler (departments/marketing_comms/agents.py's
on_task_received) can't hold a request open that long. See app/api/veo.py
for the polling side that calls check_video_generation later, in a
completely separate request.
"""

from __future__ import annotations

from google import genai
from google.genai.types import GenerateVideosConfig, GenerateVideosOperation

from app.config import settings


def _client() -> genai.Client:
    return genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.vertex_location)


async def start_video_generation(org_id: str, prompt: str) -> str:
    """Kicks off a Veo operation and returns its resumable operation name
    (NOT the finished video) — store this, don't wait on it here."""
    output_gcs_uri = f"gs://{settings.corporate_attachments_bucket}/orgs/{org_id}/veo"
    operation = await _client().aio.models.generate_videos(
        model=settings.corporate_veo_model,
        prompt=prompt,
        config=GenerateVideosConfig(aspect_ratio="16:9", output_gcs_uri=output_gcs_uri),
    )
    return operation.name


async def check_video_generation(operation_name: str) -> str | None:
    """Returns the gs:// video URI once the operation has finished, or None
    if it's still running. Raises RuntimeError if the operation itself
    failed — callers treat that as a normal failed request, same as any
    other generation failure."""
    operation = await _client().aio.operations.get(GenerateVideosOperation(name=operation_name))
    if not operation.done:
        return None
    if operation.error:
        raise RuntimeError(f"Veo generation failed: {operation.error}")
    return operation.result.generated_videos[0].video.uri
