"""Covers ADR-0013's per-org settings and pending-attachment store helpers."""

from unittest.mock import MagicMock, patch

from app.models import Attachment
from app.services import store


def test_get_org_settings_defaults_when_doc_absent():
    mock_doc = MagicMock()
    mock_doc.get.return_value.exists = False
    with patch("app.services.store.org_doc", return_value=mock_doc):
        result = store.get_org_settings("org-test")
    assert result.daily_gemini_call_limit is None


def test_get_org_settings_reads_existing_limit():
    mock_doc = MagicMock()
    mock_doc.get.return_value.exists = True
    mock_doc.get.return_value.to_dict.return_value = {"dailyGeminiCallLimit": 2}
    with patch("app.services.store.org_doc", return_value=mock_doc):
        result = store.get_org_settings("org-test")
    assert result.daily_gemini_call_limit == 2


def test_update_org_settings_writes_camel_case():
    mock_doc = MagicMock()
    with patch("app.services.store.org_doc", return_value=mock_doc):
        store.update_org_settings("org-test", daily_gemini_call_limit=10)
    written = mock_doc.set.call_args.args[0]
    assert written["dailyGeminiCallLimit"] == 10


def test_pending_attachment_round_trips():
    mock_doc = MagicMock()
    mock_doc.get.return_value.exists = True
    mock_doc.get.return_value.to_dict.return_value = {
        "pendingAttachment": {"mimeType": "image/png", "gcsUri": "gs://bucket/x"}
    }
    with patch("app.services.store.org_doc", return_value=mock_doc):
        result = store.get_ceo_pending_attachment("org-test")
    assert result == Attachment(mime_type="image/png", gcs_uri="gs://bucket/x")


def test_set_pending_attachment_none_clears_it():
    mock_doc = MagicMock()
    with patch("app.services.store.org_doc", return_value=mock_doc):
        store.set_ceo_pending_attachment("org-test", None)
    written = mock_doc.set.call_args.args[0]
    assert written["pendingAttachment"] is None
