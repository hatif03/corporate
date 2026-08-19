from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import Trigger, TriggerType

client = TestClient(app)


def _fake_webhook_trigger(secret: str = "shh") -> Trigger:
    return Trigger(
        id="trig-1",
        name="Slack incident hook",
        type=TriggerType.WEBHOOK,
        target_agent="engineering_sre",
        payload_template="Incident reported via Slack: {payload}",
        webhook_secret=secret,
        enabled=True,
    )


def test_create_schedule_trigger_requires_cron():
    with patch("app.api.triggers.store.create_trigger"):
        response = client.post(
            "/api/org/demo/triggers",
            json={
                "name": "Hourly digest",
                "type": "schedule",
                "target_agent": "executive",
                "payload_template": "",
            },
        )
    assert response.status_code == 400


def test_create_schedule_trigger_succeeds_with_cron():
    with patch("app.api.triggers.store.create_trigger") as mock_create:
        response = client.post(
            "/api/org/demo/triggers",
            json={
                "name": "Hourly digest",
                "type": "schedule",
                "target_agent": "executive",
                "payload_template": "",
                "cron": "0 * * * *",
            },
        )
    assert response.status_code == 200
    assert mock_create.called
    assert response.json()["cron"] == "0 * * * *"


def test_webhook_rejects_wrong_secret():
    with patch("app.api.triggers.store.get_trigger", return_value=_fake_webhook_trigger()):
        response = client.post(
            "/api/org/demo/triggers/trig-1/webhook",
            headers={"X-Trigger-Secret": "wrong"},
            content=b"payload",
        )
    assert response.status_code == 401


def test_webhook_dispatches_with_correct_secret():
    with (
        patch("app.api.triggers.store.get_trigger", return_value=_fake_webhook_trigger()),
        patch("app.api.triggers.store.mark_trigger_fired") as mock_mark,
        patch("app.api.triggers.pubsub_client.publish_message") as mock_publish,
    ):
        response = client.post(
            "/api/org/demo/triggers/trig-1/webhook",
            headers={"X-Trigger-Secret": "shh"},
            content=b"auth-service is down",
        )
    assert response.status_code == 200
    assert mock_publish.called
    call_kwargs = mock_publish.call_args.kwargs
    assert call_kwargs["to"] == "engineering_sre"
    assert "auth-service is down" in call_kwargs["body"]
    assert mock_mark.called


def test_disabled_webhook_is_rejected():
    disabled = _fake_webhook_trigger()
    disabled.enabled = False
    with patch("app.api.triggers.store.get_trigger", return_value=disabled):
        response = client.post(
            "/api/org/demo/triggers/trig-1/webhook",
            headers={"X-Trigger-Secret": "shh"},
            content=b"payload",
        )
    assert response.status_code == 403


def test_internal_fire_dispatches_scheduled_trigger():
    schedule_trigger = Trigger(
        id="trig-2",
        name="Hourly digest",
        type=TriggerType.SCHEDULE,
        target_agent="executive",
        payload_template="Produce today's digest.",
        cron="0 * * * *",
        enabled=True,
    )
    with (
        patch("app.api.triggers.store.get_trigger", return_value=schedule_trigger),
        patch("app.api.triggers.store.mark_trigger_fired"),
        patch("app.api.triggers.pubsub_client.publish_message") as mock_publish,
    ):
        response = client.post("/internal/triggers/demo/trig-2/fire")
    assert response.status_code == 200
    assert response.json()["fired"] is True
    assert mock_publish.call_args.kwargs["to"] == "executive"
