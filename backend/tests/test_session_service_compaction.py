"""Covers FirestoreSessionService._persist's compaction wiring — the
compaction logic itself is tested in test_compaction.py; this only checks
_persist calls it at the right time and never lets a compaction failure
escape into a real turn."""

from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.sessions.session import Session

from app.services.session_service import FirestoreSessionService, _json_safe


def _session() -> Session:
    return Session(app_name="corporate", user_id="org-test", id="finance_audit", state={}, events=[])


async def test_persist_skips_compaction_when_under_threshold():
    service = FirestoreSessionService()
    mock_doc = MagicMock()
    with (
        patch("app.services.session_service.org_doc", return_value=mock_doc),
        patch("app.services.session_service.compaction.should_compact", return_value=False),
        patch("app.services.session_service.compaction.compact_events") as mock_compact,
    ):
        await service._persist("org-test", _session())

    mock_compact.assert_not_called()
    mock_doc.set.assert_called_once()


async def test_persist_compacts_when_over_threshold():
    service = FirestoreSessionService()
    session = _session()
    mock_doc = MagicMock()
    with (
        patch("app.services.session_service.org_doc", return_value=mock_doc),
        patch("app.services.session_service.compaction.should_compact", return_value=True),
        patch("app.services.session_service.compaction.compact_events", new=AsyncMock(return_value=[])) as mock_compact,
    ):
        await service._persist("org-test", session)

    mock_compact.assert_called_once_with("org-test", session.events)
    mock_doc.set.assert_called_once()


async def test_persist_swallows_compaction_failure_and_still_writes():
    service = FirestoreSessionService()
    session = _session()
    mock_doc = MagicMock()
    with (
        patch("app.services.session_service.org_doc", return_value=mock_doc),
        patch("app.services.session_service.compaction.should_compact", return_value=True),
        patch(
            "app.services.session_service.compaction.compact_events",
            new=AsyncMock(side_effect=RuntimeError("summarizer blew up")),
        ),
        patch("app.services.session_service.store.log_activity") as mock_log,
    ):
        await service._persist("org-test", session)  # must not raise

    mock_log.assert_called_once()
    assert mock_log.call_args.args[2] == "compaction-failed"
    mock_doc.set.assert_called_once()


class _Unserializable:
    def __str__(self) -> str:
        return "<unserializable-thing>"


def test_json_safe_converts_objects_json_cannot_encode():
    assert _json_safe({"grounding_metadata": _Unserializable()}) == {
        "grounding_metadata": "<unserializable-thing>"
    }


async def test_persist_survives_a_raw_sdk_object_nested_in_an_event_dump():
    """Regression test: reproduced live against real Vertex AI — a Google
    Search-grounded turn's event carried a raw google.genai.types.
    GroundingMetadata object nested inside its own model_dump(mode="json")
    output (the shape is search-response-dependent, so this uses a
    stand-in object rather than the real SDK type), which Firestore's
    client can't encode and previously crashed the whole turn."""
    service = FirestoreSessionService()
    session = _session()
    fake_event = MagicMock()
    fake_event.model_dump.return_value = {"content": {"parts": [{"grounding_metadata": _Unserializable()}]}}
    session.events = [fake_event]
    mock_doc = MagicMock()
    with (
        patch("app.services.session_service.org_doc", return_value=mock_doc),
        patch("app.services.session_service.compaction.should_compact", return_value=False),
    ):
        await service._persist("org-test", session)  # must not raise

    written = mock_doc.set.call_args.args[0]
    assert written["events"][0]["content"]["parts"][0]["grounding_metadata"] == "<unserializable-thing>"
