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
