from unittest.mock import MagicMock, patch

from google.api_core.exceptions import Conflict

from app.services import store


def test_mark_message_processed_true_on_first_sight():
    mock_doc = MagicMock()
    with patch("app.services.store.org_doc", return_value=mock_doc):
        result = store.mark_message_processed("org-test", "finance_audit", "msg-1")

    assert result is True
    mock_doc.create.assert_called_once()


def test_mark_message_processed_false_on_redelivery():
    mock_doc = MagicMock()
    mock_doc.create.side_effect = Conflict("already exists")
    with patch("app.services.store.org_doc", return_value=mock_doc):
        result = store.mark_message_processed("org-test", "finance_audit", "msg-1")

    assert result is False


def test_mark_message_processed_keys_by_agent_and_message():
    mock_doc = MagicMock()
    with patch("app.services.store.org_doc", return_value=mock_doc) as mock_org_doc:
        store.mark_message_processed("org-test", "finance_audit", "msg-1")

    mock_org_doc.assert_called_once_with("org-test", "processed_messages", "finance_audit:msg-1")
