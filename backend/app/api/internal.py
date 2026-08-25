"""Pub/Sub push target. See docs/adr/0003-firestore-pubsub-for-state-and-messaging.md
and app/services/dispatch.py for the shared handler this delegates to.

OIDC verification: Cloud Run's own IAM-based push authentication (the
Pub/Sub push subscription is created with --push-auth-service-account and
Cloud Run requires authentication) is the primary control — this route does
not additionally decode the OIDC token itself. If deploying with
--allow-unauthenticated, add explicit token verification here first.

Every response is 200, even on a malformed envelope (see ADR-0011): Pub/Sub
retries push delivery on ANY non-2xx status, not just 5xx, so a genuinely
malformed message (bad JSON, missing orgId, schema mismatch) would retry
forever otherwise — retrying can't fix a permanently-malformed payload, so
it's logged and acked instead.
"""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Request

from app.models import Message
from app.services.dispatch import handle_agent_turn

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/agent-turn/{agent_id}")
async def agent_turn(agent_id: str, request: Request) -> dict:
    try:
        envelope = await request.json()
        pubsub_message = envelope.get("message")
        if not pubsub_message or "data" not in pubsub_message:
            raise ValueError("malformed Pub/Sub push envelope")

        attributes = pubsub_message.get("attributes", {})
        org_id = attributes.get("orgId")
        if not org_id:
            raise ValueError("missing orgId attribute")

        payload = json.loads(base64.b64decode(pubsub_message["data"]))
        message = Message(**payload)
    except Exception as exc:  # noqa: BLE001 - a malformed envelope must never retry forever, see module docstring
        # No org_id to scope an activity_log entry to at this point (that's
        # often exactly what failed to parse) — Cloud Run's own request logs
        # cover this rare case, acked-not-retried is what actually matters.
        return {"status": "rejected", "reason": str(exc)}

    await handle_agent_turn(org_id, agent_id, message)
    return {"status": "ok"}
