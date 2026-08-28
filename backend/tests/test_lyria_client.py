"""Lyria break-room music generation (app/services/lyria_client.py,
ADR-0019) — no Python SDK for Lyria yet, so this calls the raw Vertex AI
predict REST endpoint directly; mocks httpx and google.auth the same way
test_integration_broker.py mocks httpx for the (also-raw-REST) integration
broker calls.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import lyria_client

_FAKE_WAV_BYTES = b"RIFF....WAVEfmt "
_FAKE_AUDIO_B64 = base64.b64encode(_FAKE_WAV_BYTES).decode()


def _mock_auth():
    creds = MagicMock()
    creds.token = "fake-access-token"
    return patch("app.services.lyria_client.google.auth.default", return_value=(creds, "some-project"))


async def test_generate_ambient_track_returns_decoded_audio_bytes():
    fake_response = httpx.Response(
        200,
        json={"predictions": [{"audioContent": _FAKE_AUDIO_B64, "mimeType": "audio/wav"}]},
        request=httpx.Request("POST", "https://example.com"),
    )
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with (
        _mock_auth(),
        patch("app.services.lyria_client.httpx.AsyncClient", return_value=mock_async_client),
    ):
        result = await lyria_client.generate_ambient_track("calm office music")

    assert result == _FAKE_WAV_BYTES
    call_kwargs = mock_async_client.__aenter__.return_value.post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer fake-access-token"
    assert call_kwargs["json"]["instances"][0]["prompt"] == "calm office music"


async def test_generate_ambient_track_raises_on_empty_predictions():
    fake_response = httpx.Response(200, json={"predictions": []}, request=httpx.Request("POST", "https://example.com"))
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with (
        _mock_auth(),
        patch("app.services.lyria_client.httpx.AsyncClient", return_value=mock_async_client),
    ):
        with pytest.raises(RuntimeError, match="no predictions"):
            await lyria_client.generate_ambient_track("calm office music")


async def test_generate_ambient_track_raises_on_http_error():
    fake_response = httpx.Response(503, text="service unavailable", request=httpx.Request("POST", "https://example.com"))
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with (
        _mock_auth(),
        patch("app.services.lyria_client.httpx.AsyncClient", return_value=mock_async_client),
    ):
        with pytest.raises(httpx.HTTPStatusError):
            await lyria_client.generate_ambient_track("calm office music")
