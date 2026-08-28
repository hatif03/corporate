"""Covers ADR-0013's dispatch attachment upload leg and the new /settings routes."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dispatch_without_attachment_publishes_plain_message():
    with patch("app.api.org.pubsub_client.publish_message") as mock_publish:
        mock_publish.return_value.id = "msg-1"
        response = client.post("/api/org/demo/dispatch", json={"text": "do the thing"})
    assert response.status_code == 200
    assert mock_publish.call_args.kwargs["attachment"] is None


def test_dispatch_with_attachment_uploads_then_publishes_gcs_reference():
    with (
        patch("app.api.org.storage_client.upload_attachment", return_value="gs://bucket/orgs/demo/attachments/x") as mock_upload,
        patch("app.api.org.pubsub_client.publish_message") as mock_publish,
    ):
        mock_publish.return_value.id = "msg-1"
        response = client.post(
            "/api/org/demo/dispatch",
            json={"text": "fix this", "attachment_data_b64": "aGVsbG8=", "attachment_mime_type": "image/png"},
        )
    assert response.status_code == 200
    assert mock_upload.call_args.args == ("demo", "image/png", b"hello")
    published_attachment = mock_publish.call_args.kwargs["attachment"]
    assert published_attachment.gcs_uri == "gs://bucket/orgs/demo/attachments/x"


def test_dispatch_with_attachment_missing_mime_type_rejected():
    response = client.post("/api/org/demo/dispatch", json={"text": "fix this", "attachment_data_b64": "aGVsbG8="})
    assert response.status_code == 400


def test_get_settings_returns_defaults_when_unset():
    with patch("app.api.org.store.get_org_settings") as mock_get:
        from app.models import OrgSettings

        mock_get.return_value = OrgSettings()
        response = client.get("/api/org/demo/settings")
    assert response.status_code == 200
    assert response.json()["dailyGeminiCallLimit"] is None


def test_update_settings_rejects_zero_limit():
    response = client.post("/api/org/demo/settings", json={"daily_gemini_call_limit": 0})
    assert response.status_code == 400


def test_pause_and_resume_agent():
    from app.models import Agent

    agent = Agent(id="engineering_sre", name="SRE", department="engineering_sre")
    with (
        patch("app.api.agents.store.get_agent", return_value=agent),
        patch("app.api.agents.store.set_agent_paused") as mock_set,
    ):
        response = client.post("/api/org/demo/agents/engineering_sre/pause")
    assert response.status_code == 200
    assert response.json() == {"paused": True}
    assert mock_set.call_args.args == ("demo", "engineering_sre", True)


def test_pause_unknown_agent_404s():
    with patch("app.api.agents.store.get_agent", return_value=None):
        response = client.post("/api/org/demo/agents/nope/pause")
    assert response.status_code == 404


def test_update_persona_writes_only_provided_fields():
    from app.models import Agent

    agent = Agent(id="engineering_sre", name="SRE", department="engineering_sre")
    renamed = Agent(id="engineering_sre", name="New Name", department="engineering_sre")
    with (
        patch("app.api.agents.store.get_agent", side_effect=[agent, renamed]),
        patch("app.api.agents.store.update_agent_persona") as mock_update,
    ):
        response = client.patch("/api/org/demo/agents/engineering_sre", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    mock_update.assert_called_once_with("demo", "engineering_sre", name="New Name")


def test_update_persona_unknown_agent_404s():
    with patch("app.api.agents.store.get_agent", return_value=None):
        response = client.patch("/api/org/demo/agents/nope", json={"name": "X"})
    assert response.status_code == 404


def test_list_agent_skills_returns_store_contents():
    skills = [{"id": "s1", "title": "Escalate P1s", "instructions": "Page on-call.", "createdAt": "2026-01-01"}]
    with patch("app.api.agents.store.list_agent_custom_skills", return_value=skills):
        response = client.get("/api/org/demo/agents/engineering_sre/skills")
    assert response.status_code == 200
    assert response.json() == skills


def test_add_agent_skill_unknown_agent_404s():
    with patch("app.api.agents.store.get_agent", return_value=None):
        response = client.post("/api/org/demo/agents/nope/skills", json={"title": "X", "instructions": "Y"})
    assert response.status_code == 404


def test_add_agent_skill_writes_through_store():
    from app.models import Agent

    agent = Agent(id="engineering_sre", name="Engineering & SRE Lead", department="engineering_sre")
    with (
        patch("app.api.agents.store.get_agent", return_value=agent),
        patch("app.api.agents.store.add_agent_custom_skill", return_value="skill-1") as mock_add,
    ):
        response = client.post(
            "/api/org/demo/agents/engineering_sre/skills", json={"title": "Escalate P1s", "instructions": "Page on-call."}
        )
    assert response.status_code == 200
    assert response.json()["id"] == "skill-1"
    mock_add.assert_called_once_with("demo", "engineering_sre", "Escalate P1s", "Page on-call.")


def test_delete_agent_skill_calls_store():
    with patch("app.api.agents.store.delete_agent_custom_skill") as mock_delete:
        response = client.delete("/api/org/demo/agents/engineering_sre/skills/skill-1")
    assert response.status_code == 200
    mock_delete.assert_called_once_with("demo", "engineering_sre", "skill-1")


def test_approve_agent_skill_calls_store():
    """The review/approve half of an agent's own propose_skill loop
    (tools/universal.py) — flips a pending skill to active."""
    with patch("app.api.agents.store.approve_agent_custom_skill") as mock_approve:
        response = client.post("/api/org/demo/agents/engineering_sre/skills/skill-1/approve")
    assert response.status_code == 200
    assert response.json() == {"approved": True}
    mock_approve.assert_called_once_with("demo", "engineering_sre", "skill-1")


def test_update_settings_accepts_valid_limit():
    with (
        patch("app.api.org.store.update_org_settings") as mock_update,
        patch("app.api.org.store.get_org_settings") as mock_get,
    ):
        from app.models import OrgSettings

        mock_get.return_value = OrgSettings(daily_gemini_call_limit=2)
        response = client.post("/api/org/demo/settings", json={"daily_gemini_call_limit": 2})
    assert response.status_code == 200
    assert mock_update.call_args.kwargs["daily_gemini_call_limit"] == 2
    assert response.json()["dailyGeminiCallLimit"] == 2
