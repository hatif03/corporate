"""scripts/seed.py's default self-check/memory-curation triggers (the
proactive-heartbeat pattern adapted from OpenClaw/Hermes-agent, see
docs/adr/0019-...) — verifies they're shaped correctly and actually fire
cleanly through the existing trigger-dispatch path (app/api/triggers.py),
the same mechanism any other schedule trigger already uses.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import TriggerType
from scripts.seed import DEFAULT_TRIGGERS, seed_default_triggers

client = TestClient(app)


def test_default_triggers_target_ceo_on_a_schedule():
    assert len(DEFAULT_TRIGGERS) == 2
    for trigger in DEFAULT_TRIGGERS:
        assert trigger.target_agent == "ceo"
        assert trigger.type == TriggerType.SCHEDULE
        assert trigger.cron  # required for schedule triggers, app/api/triggers.py


def test_seed_default_triggers_upserts_each_one():
    with patch("scripts.seed.store.create_trigger") as mock_create:
        seed_default_triggers("demo")
    assert mock_create.call_count == len(DEFAULT_TRIGGERS)
    assert {call.args[1].id for call in mock_create.call_args_list} == {t.id for t in DEFAULT_TRIGGERS}


@pytest.mark.parametrize("trigger", DEFAULT_TRIGGERS, ids=lambda t: t.id)
def test_each_default_trigger_fires_cleanly(trigger):
    with (
        patch("app.api.triggers.store.get_trigger", return_value=trigger),
        patch("app.api.triggers.store.mark_trigger_fired"),
        patch("app.api.triggers.store.log_trigger_history"),
        patch("app.api.triggers.pubsub_client.publish_message") as mock_publish,
    ):
        response = client.post(f"/internal/triggers/demo/{trigger.id}/fire")

    assert response.status_code == 200
    assert response.json()["fired"] is True
    assert mock_publish.call_args.kwargs["to"] == "ceo"
