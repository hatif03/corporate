"""Break-room ambient music via Vertex AI's Lyria music-generation model
(ADR-0019). No Python SDK method for Lyria yet — confirmed the installed
google-genai SDK's Models/AsyncModels expose generate_images/generate_videos
but nothing music-shaped — so this calls the raw Vertex AI predict REST
endpoint directly with the same ADC credentials every other Vertex call in
this app already uses, via google.auth (not a new auth mechanism).
"""

from __future__ import annotations

import base64

import google.auth
import google.auth.transport.requests
import httpx

from app.config import settings

_PREDICT_URL = (
    "https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}"
    "/publishers/google/models/{model}:predict"
)


def _access_token() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


async def generate_ambient_track(prompt: str) -> bytes:
    """Returns raw WAV bytes for a ~30s clip. Raises (httpx.HTTPStatusError,
    RuntimeError) on any failure — callers treat that as a normal failed
    request, not a special case; see app/api/breakroom.py.

    Request body and response shape confirmed against a REAL live call (not
    docs/search-snippet prose, which turned out to be wrong about the
    response field name — a search summary said `audioContent`; the actual
    live response uses `bytesBase64Encoded`, same convention as Imagen).
    `parameters` stays empty — no `sample_count`, that was an incorrect
    carry-over from Imagen-style params. Timeout is 90s, not 60s: a real
    clip can take up to that long to generate."""
    url = _PREDICT_URL.format(
        location=settings.vertex_location, project=settings.google_cloud_project, model=settings.corporate_lyria_model
    )
    body = {"instances": [{"prompt": prompt}], "parameters": {}}

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, json=body, headers={"Authorization": f"Bearer {_access_token()}"})
    response.raise_for_status()

    predictions = response.json().get("predictions", [])
    if not predictions:
        raise RuntimeError("Lyria returned no predictions")
    return base64.b64decode(predictions[0]["bytesBase64Encoded"])
