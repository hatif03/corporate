"""app/services/oauth_providers.py's exchange_code — specifically the new
_safe_json guard (ADR-0019's Part 4: a non-JSON provider response, e.g. an
HTML error page, previously raised an uncaught json.JSONDecodeError instead
of the ValueError every caller of exchange_code already expects on failure).
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services import oauth_providers


async def test_exchange_code_raises_value_error_on_non_json_response():
    fake_response = httpx.Response(200, text="<html>not json</html>", request=httpx.Request("POST", "https://example.com"))
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with (
        patch.object(oauth_providers, "_client_secret", return_value="shh"),
        patch("app.services.oauth_providers.httpx.AsyncClient", return_value=mock_async_client),
    ):
        with pytest.raises(ValueError, match="non-JSON response"):
            await oauth_providers.exchange_code("slack", "code123", "https://backend/callback")


async def test_exchange_code_builds_client_with_a_timeout():
    fake_response = httpx.Response(200, json={"ok": True, "access_token": "xoxb-fake"}, request=httpx.Request("POST", "https://example.com"))
    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with (
        patch.object(oauth_providers, "_client_secret", return_value="shh"),
        patch("app.services.oauth_providers.httpx.AsyncClient", return_value=mock_async_client) as mock_ctor,
    ):
        token = await oauth_providers.exchange_code("slack", "code123", "https://backend/callback")

    assert token == "xoxb-fake"
    assert mock_ctor.call_args.kwargs["timeout"] == oauth_providers._TIMEOUT_SECONDS
