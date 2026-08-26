"""Covers app/services/compaction.py — adapted from opencode's compaction
pattern (MIT, anomalyco/opencode — see /THIRD_PARTY_SKILLS.md and
docs/adr/0015). Pure logic, no network: the summarizer itself is
monkeypatched everywhere except where its absence is exactly what's being
tested (the budget-exhausted deliberate-failure-path case)."""

from unittest.mock import patch

from google.adk.events.event import Event
from google.genai import types

from app.models import OrgSettings
from app.services import compaction


def _event(author: str, text: str) -> Event:
    return Event(author=author, content=types.Content(role=author, parts=[types.Part(text=text)]))


def test_should_compact_false_under_threshold():
    events = [_event("user", "hi")]
    assert compaction.should_compact(events) is False


def test_should_compact_true_over_threshold():
    events = [_event("user", "x" * 1000) for _ in range(10)]
    with patch("app.services.compaction.COMPACTION_TRIGGER_BYTES", 500):
        assert compaction.should_compact(events) is True


def test_split_tail_keeps_whole_events_within_budget():
    events = [_event("user", f"turn {i}") for i in range(10)]
    with patch("app.services.compaction.PRESERVE_TAIL_BYTES", 300):
        old, tail = compaction._split_tail(events)

    assert old + tail == events  # nothing lost, nothing duplicated
    assert len(tail) < len(events)  # the budget actually constrained something
    # every event in the tail is untouched (kept verbatim, not truncated)
    for e in tail:
        assert e in events


async def test_compact_events_summarizes_old_turns_and_chains_prior_summary():
    events = [_event("user", f"turn {i}") for i in range(10)]

    async def fake_summarize(blob, previous_summary):
        assert previous_summary is None
        return "summary of early turns"

    with (
        patch("app.services.compaction.PRESERVE_TAIL_BYTES", 100),
        patch("app.services.compaction._summarize", side_effect=fake_summarize),
        patch("app.services.compaction.store.get_org_settings", return_value=OrgSettings()),
        patch("app.services.compaction.store.increment_and_check_gemini_budget", return_value=True),
    ):
        result = await compaction.compact_events("org-test", events)

    assert result[0].author == "user"
    assert compaction.SUMMARY_MARKER in result[0].content.parts[0].text
    assert "summary of early turns" in result[0].content.parts[0].text
    assert len(result) < len(events)


async def test_compact_events_chains_off_a_prior_summary():
    prior_summary_event = _event("user", f"{compaction.SUMMARY_MARKER}\nold summary text")
    events = [prior_summary_event] + [_event("user", f"turn {i}") for i in range(10)]

    captured = {}

    async def fake_summarize(blob, previous_summary):
        captured["previous_summary"] = previous_summary
        return "new combined summary"

    with (
        patch("app.services.compaction.PRESERVE_TAIL_BYTES", 100),
        patch("app.services.compaction._summarize", side_effect=fake_summarize),
        patch("app.services.compaction.store.get_org_settings", return_value=OrgSettings()),
        patch("app.services.compaction.store.increment_and_check_gemini_budget", return_value=True),
    ):
        await compaction.compact_events("org-test", events)

    assert captured["previous_summary"] == "old summary text"


async def test_compact_events_skips_compaction_when_budget_exhausted():
    events = [_event("user", f"turn {i}") for i in range(10)]
    with (
        patch("app.services.compaction.PRESERVE_TAIL_BYTES", 100),
        patch("app.services.compaction.store.get_org_settings", return_value=OrgSettings()),
        patch("app.services.compaction.store.increment_and_check_gemini_budget", return_value=False),
    ):
        result = await compaction.compact_events("org-test", events)

    assert result == events  # unchanged, no exception


async def test_compact_events_returns_unchanged_when_tail_alone_exceeds_budget():
    events = [_event("user", "just one turn")]
    with patch("app.services.compaction.PRESERVE_TAIL_BYTES", 10_000_000):
        result = await compaction.compact_events("org-test", events)
    assert result == events
