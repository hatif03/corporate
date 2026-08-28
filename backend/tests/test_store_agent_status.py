"""Regression test for a real production bug found while auditing worker
observability: before this fix, every spawned worker's before_agent_callback
crashed with a Firestore NotFound (workers have no backing agents/{id} doc),
failing every worker turn before it ever ran a tool."""

from unittest.mock import MagicMock, patch

from google.api_core.exceptions import NotFound

from app.models import AgentStatus
from app.services import store


def test_update_agent_status_swallows_not_found_for_docless_ids():
    mock_doc = MagicMock()
    mock_doc.update.side_effect = NotFound("no such document")
    with patch("app.services.store.org_doc", return_value=mock_doc):
        store.update_agent_status("org-test", "worker-abc123", AgentStatus.THINKING)  # must not raise


def test_update_agent_status_still_updates_existing_agent_docs():
    mock_doc = MagicMock()
    with patch("app.services.store.org_doc", return_value=mock_doc):
        store.update_agent_status("org-test", "ceo", AgentStatus.WORKING, action="using send_message")

    update_arg = mock_doc.update.call_args.args[0]
    assert update_arg["status"] == AgentStatus.WORKING.value
    assert update_arg["action"] == "using send_message"
