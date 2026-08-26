"""Realtime voice dispatch to the CEO — a WebSocket relay to Vertex AI's
Live API (google-genai's client.aio.live.connect(), confirmed available on
Vertex specifically, GA since 2025-12-13 — not just the Developer API).
Vertex's Live API has no ephemeral-token path (the SDK raises ValueError
for auth_tokens.create() under vertexai=True), so a backend relay holding
real ADC credentials is the only legitimate architecture here, not a
shortcut: the browser never touches a credential, only PCM audio bytes
over this WebSocket. See docs/adr/0016-agent-capability-expansion.md and
PROJECT_HISTORY.md for the research this is built on.

v1 scope: a real-time voice conversation with the CEO's own persona (its
system prompt, so it answers in character), not yet wired to the CEO's
actual tools (create_task, etc.) — that needs routing through ADK's
Runner.run_live/LiveRequestQueue instead of the raw genai client, which is
a real follow-up, not implemented here to avoid shipping an unverified
integration.

Browsers can't set arbitrary headers on a WebSocket handshake, so auth is
a query-param Firebase ID token (?token=...) verified the same way
require_org_member verifies one, just as a plain function instead of an
HTTP dependency (FastAPI's header-based Depends() machinery is for HTTP
routes).
"""

from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from firebase_admin import auth as firebase_auth
from google import genai
from google.genai import types

from app.adk_agents.factory import CEO_SYSTEM_PROMPT
from app.config import settings
from app.services import store
from app.services.auth import _ensure_app

router = APIRouter()

# Vertex AI's Live API model id — distinct from the Developer API's own
# naming (confirmed via the installed SDK's own docstring + Google's
# Vertex docs). Preview-suffixed model names have churned before; confirm
# against docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-live-api
# if this ever 404s.
VOICE_MODEL = "gemini-2.0-flash-live-preview-04-09"


async def _authorized_uid(websocket: WebSocket, org_id: str) -> str | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    _ensure_app()
    try:
        decoded = firebase_auth.verify_id_token(token)
    except (
        firebase_auth.InvalidIdTokenError,
        firebase_auth.ExpiredIdTokenError,
        firebase_auth.RevokedIdTokenError,
    ):
        return None
    uid = decoded["uid"]
    if store.get_member_role(org_id, uid) is None:
        return None
    return uid


@router.websocket("/ws/voice/{org_id}")
async def voice_relay(websocket: WebSocket, org_id: str) -> None:
    uid = await _authorized_uid(websocket, org_id)
    if uid is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()

    client = genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.vertex_location)
    config = types.LiveConnectConfig(response_modalities=["AUDIO"], system_instruction=CEO_SYSTEM_PROMPT)

    try:
        async with client.aio.live.connect(model=VOICE_MODEL, config=config) as session:

            async def pump_browser_to_model() -> None:
                while True:
                    message = await websocket.receive_json()
                    if message.get("type") == "audio":
                        audio_bytes = base64.b64decode(message["data"])
                        await session.send_realtime_input(audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000"))
                    elif message.get("type") == "end":
                        return

            async def pump_model_to_browser() -> None:
                async for response in session.receive():
                    if response.data:
                        await websocket.send_json({"type": "audio", "data": base64.b64encode(response.data).decode()})
                    if response.text:
                        await websocket.send_json({"type": "text", "data": response.text})

            pump_in = asyncio.create_task(pump_browser_to_model())
            pump_out = asyncio.create_task(pump_model_to_browser())
            done, pending = await asyncio.wait([pump_in, pump_out], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001 - best-effort close, connection may already be gone
            pass
