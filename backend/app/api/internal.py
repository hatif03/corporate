"""Pub/Sub push target. See docs/adr/0003-firestore-pubsub-for-state-and-messaging.md
and app/services/dispatch.py for the shared handler this delegates to.

OIDC verification: Cloud Run's own IAM-based push authentication (the
Pub/Sub push subscription is created with --push-auth-service-account and
Cloud Run requires authentication) is the primary control — this route does
not additionally decode the OIDC token itself. If deploying with
--allow-unauthenticated, add explicit token verification here first.
"""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, HTTPException, Request

from app.models import Message
from app.services.dispatch import handle_agent_turn

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/agent-turn/{agent_id}")
async def agent_turn(agent_id: str, request: Request) -> dict:
    envelope = await request.json()
    pubsub_message = envelope.get("message")
    if not pubsub_message or "data" not in pubsub_message:
        raise HTTPException(status_code=400, detail="malformed Pub/Sub push envelope")

    attributes = pubsub_message.get("attributes", {})
    org_id = attributes.get("orgId")
    if not org_id:
        raise HTTPException(status_code=400, detail="missing orgId attribute")

    payload = json.loads(base64.b64decode(pubsub_message["data"]))
    message = Message(**payload)

    await handle_agent_turn(org_id, agent_id, message)
    return {"status": "ok"}
