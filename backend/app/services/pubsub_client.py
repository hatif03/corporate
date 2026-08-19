"""The single chokepoint for inter-agent messaging.

publish_message() is the ONLY function anywhere in this codebase allowed to
increment `hops`, derive `requires_reply`, or resolve the "ceo"/"broadcast"
aliases to real agent ids. Never construct/publish a message any other way.
See ADR-0003 and .cursor/rules/firestore-access.mdc.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from google.cloud import pubsub_v1

from app.config import settings
from app.models import Act, REPLY_OBLIGATING_ACTS, Message
from app.services import store

HOP_LIMIT = 12


class LoopTerminatedError(Exception):
    """Raised when a conversation exceeds HOP_LIMIT — the caller should flag
    the originating task for human review rather than retry."""


@lru_cache
def _publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


@lru_cache
def _topic_path() -> str:
    return _publisher().topic_path(settings.google_cloud_project, settings.corporate_pubsub_topic)


def _resolve_recipient(org_id: str, to: str) -> str:
    """'ceo' and 'broadcast' are the only literal aliases; everything else
    must already be a real agent id."""
    if to in ("ceo", "broadcast"):
        return to
    agent = store.get_agent(org_id, to)
    if agent is None:
        raise ValueError(f"publish_message: unknown recipient agent id '{to}' in org '{org_id}'")
    return to


def _next_hops(org_id: str, conversation: str) -> int:
    prior = [m for m in store.list_messages(org_id, limit=500) if m.conversation == conversation]
    return (max((m.hops for m in prior), default=0)) + 1


def publish_message(
    org_id: str,
    from_agent: str,
    to: str,
    act: Act,
    subject: str,
    body: str,
    conversation: str | None = None,
    in_reply_to: str | None = None,
    needs_human: bool = False,
) -> Message:
    """Publish one inter-agent message. Raises LoopTerminatedError instead of
    publishing once a conversation's hop count exceeds HOP_LIMIT."""
    to = _resolve_recipient(org_id, to)
    conversation = conversation or str(uuid.uuid4())
    hops = _next_hops(org_id, conversation)

    if hops > HOP_LIMIT:
        store.log_activity(
            org_id,
            from_agent,
            "loop-terminated",
            f"conversation {conversation} exceeded {HOP_LIMIT} hops",
        )
        raise LoopTerminatedError(f"conversation '{conversation}' exceeded hop limit {HOP_LIMIT}")

    message = Message(
        id=f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        conversation=conversation,
        in_reply_to=in_reply_to,
        **{"from": from_agent},
        to=to,
        act=act,
        subject=subject,
        body=body,
        hops=hops,
        requires_reply=act in REPLY_OBLIGATING_ACTS,
        needs_human=needs_human,
    )

    payload = message.model_dump_json(by_alias=True).encode("utf-8")
    attributes = {"orgId": org_id, "to": to, "from": from_agent, "act": act.value}

    if settings.local_dev:
        # Local dev: skip the network round-trip, hand straight to the pull-loop handler.
        from app.services.pubsub_local import enqueue_local

        enqueue_local(org_id, message)
    else:
        future = _publisher().publish(_topic_path(), payload, **attributes)
        message.pubsub_message_id = future.result()

    store.save_message(org_id, message)
    return message
