"""Break Room ambient music generation (Lyria via Vertex AI, ADR-0019) — a
small "have some fun" feature tied to the office floor's Break Room zone,
not any department's actual task pipeline. Org-scoped like every other
/api/org/{org_id}/* route (see app/main.py's _org_scoped_dependency).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.lyria_client import generate_ambient_track
from app.services.storage_client import upload_playable_media

router = APIRouter(prefix="/api/org/{org_id}/breakroom", tags=["breakroom"])

_DEFAULT_PROMPT = "a calm, upbeat instrumental for an office break room, no vocals"


@router.post("/music")
async def generate_music(org_id: str, prompt: str = _DEFAULT_PROMPT) -> dict:
    try:
        audio_bytes = await generate_ambient_track(prompt)
    except Exception as exc:  # noqa: BLE001 - surfaced as a normal failed request, not a crash
        raise HTTPException(status_code=502, detail=f"music generation failed: {exc}") from None
    url = upload_playable_media(org_id, "breakroom", "audio/wav", audio_bytes)
    return {"url": url}
