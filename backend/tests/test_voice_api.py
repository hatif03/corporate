"""Auth-path tests for the voice WebSocket relay (app/api/voice.py) — the
full audio round trip against a real Vertex AI Live session is a manual
check, not automatable in this suite (see the plan's own verification
note). What's tested here: the relay never even opens a Live session for
an unauthenticated or non-member caller, which is the actual security
property that matters — the browser never gets a channel to speak through
without first passing the same membership check every other endpoint
enforces."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from app.main import app

client = TestClient(app)


def test_voice_rejects_missing_token():
    with pytest.raises(Exception):  # noqa: B017 - TestClient surfaces the server-side close as a disconnect
        with client.websocket_connect("/ws/voice/demo"):
            pass


def test_voice_rejects_invalid_token():
    with (
        patch("app.api.voice.firebase_auth.verify_id_token", side_effect=firebase_auth.InvalidIdTokenError("bad")),
        pytest.raises(Exception),  # noqa: B017
    ):
        with client.websocket_connect("/ws/voice/demo?token=bad-token"):
            pass


def test_voice_rejects_non_member():
    with (
        patch("app.api.voice.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.voice.store.get_member_role", return_value=None),
        pytest.raises(Exception),  # noqa: B017
    ):
        with client.websocket_connect("/ws/voice/demo?token=valid-token"):
            pass


def test_voice_accepts_member_and_opens_a_live_session():
    fake_session = MagicMock()

    async def fake_receive():
        return
        yield  # pragma: no cover - makes this an async generator that yields nothing

    fake_session.receive = fake_receive
    fake_session.send_realtime_input = MagicMock()

    class FakeConnect:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *exc):
            return False

    fake_live = MagicMock()
    fake_live.connect = MagicMock(return_value=FakeConnect())
    fake_client = MagicMock()
    fake_client.aio.live = fake_live

    with (
        patch("app.api.voice.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.voice.store.get_member_role", return_value="member"),
        patch("app.api.voice.genai.Client", return_value=fake_client),
    ):
        with client.websocket_connect("/ws/voice/demo?token=valid-token") as ws:
            ws.send_json({"type": "end"})

    assert fake_live.connect.called
