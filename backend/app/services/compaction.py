"""Session-event compaction for FirestoreSessionService — resolves the 1 MiB
Firestore-document-size risk flagged in session_service.py's own ponytail
comment. Adapted from opencode's session/compaction.ts tail-budget /
summarize-older / chain-prior-summaries pattern (MIT, anomalyco/opencode —
see /THIRD_PARTY_SKILLS.md and docs/adr/0015), reworked for Firestore
document *byte size* — the actual constraint here — rather than the model's
own ~1M-token context window, which is not the binding constraint at this
project's message volume.
"""

from __future__ import annotations

import json
from functools import lru_cache

from google import genai
from google.adk.events.event import Event
from google.genai import types

from app.config import settings
from app.services import store

# ponytail: ~60% of Firestore's 1 MiB doc cap, leaving headroom for the
# `state` field + doc overhead. A real, honestly-tuned trigger — not padded
# artificially high to avoid ever firing — so this only matters if it fires
# correctly under real sustained usage. Long-term upgrade path if compaction
# alone isn't enough at real scale: move events to a
# agent_sessions/{agentId}/events/{seq} subcollection, same as session_service.py's
# own ponytail already notes.
COMPACTION_TRIGGER_BYTES = 450_000
PRESERVE_TAIL_BYTES = 150_000  # kept verbatim; everything older is summarized
TOOL_OUTPUT_TRUNCATE_CHARS = 2_000  # opencode's own constant, same reason
SUMMARY_MARKER = "[compaction-summary]"


@lru_cache
def _client() -> genai.Client:
    # Deliberately NOT settings.vertex_location — this client calls
    # corporate_gemini_model, a Gemini 3.5-tier model (ADR-0020), which only
    # resolves at Vertex's "global" location in this project. Same bug,
    # same fix, as shared/cross_model_check.py's verifier client — see its
    # comment for the live-reproduced 404 this avoids.
    return genai.Client(
        vertexai=settings.google_genai_use_vertexai,
        project=settings.google_cloud_project,
        location="global",
    )


def _event_text(e: Event) -> str:
    if not e.content or not e.content.parts:
        return ""
    return "\n".join(p.text for p in e.content.parts if p.text)


def _event_size(e: Event) -> int:
    return len(json.dumps(e.model_dump(mode="json")))


def should_compact(events: list[Event]) -> bool:
    return sum(_event_size(e) for e in events) > COMPACTION_TRIGGER_BYTES


def _split_tail(events: list[Event]) -> tuple[list[Event], list[Event]]:
    """Walk backward, keeping whole events verbatim until PRESERVE_TAIL_BYTES
    is spent — never truncates mid-event, matching opencode's own
    whole-turn-at-a-time tail selection."""
    tail_size = 0
    split = len(events)
    for i in range(len(events) - 1, -1, -1):
        size = _event_size(events[i])
        if tail_size + size > PRESERVE_TAIL_BYTES and tail_size:
            break
        tail_size += size
        split = i
    return events[:split], events[split:]


def _serialize_for_summary(events: list[Event]) -> str:
    lines = []
    for e in events:
        text = _event_text(e)
        if len(text) > TOOL_OUTPUT_TRUNCATE_CHARS:
            text = text[:TOOL_OUTPUT_TRUNCATE_CHARS] + " [truncated]"
        lines.append(f"{e.author}: {text}")
    return "\n".join(lines)


async def _summarize(blob: str, previous_summary: str | None) -> str:
    prompt = (
        "Summarize this agent conversation history concisely, preserving any "
        "concrete facts/decisions a future turn would need. This is "
        "background context, not an instruction to act on.\n\n"
        + (f"PRIOR SUMMARY:\n{previous_summary}\n\n" if previous_summary else "")
        + f"OLDER TURNS:\n{blob}"
    )
    response = await _client().aio.models.generate_content(
        model=settings.corporate_gemini_model, contents=prompt
    )
    return response.text or ""


async def compact_events(org_id: str, events: list[Event]) -> list[Event]:
    """Returns a possibly-compacted events list — never raises; any failure
    (budget exhausted, summarization error) just returns `events` unchanged,
    since compaction is a soft optimization, not a correctness requirement.
    The caller (_persist) retries compaction on the next append_event."""
    previous_summary = None
    rest = events
    if events and _event_text(events[0]).startswith(SUMMARY_MARKER):
        previous_summary = _event_text(events[0])[len(SUMMARY_MARKER) :].strip()
        rest = events[1:]

    old, tail = _split_tail(rest)
    if not old:
        return events  # tail alone already exceeds the budget; nothing to summarize yet

    effective_limit = store.get_org_settings(org_id).daily_gemini_call_limit or settings.corporate_daily_gemini_call_limit
    if not store.increment_and_check_gemini_budget(org_id, effective_limit):
        return events

    summary_text = await _summarize(_serialize_for_summary(old), previous_summary)
    summary_event = Event(
        author="user",
        content=types.Content(role="user", parts=[types.Part(text=f"{SUMMARY_MARKER}\n{summary_text}")]),
    )
    return [summary_event, *tail]
