from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from google.api_core.exceptions import AlreadyExists

from app.models import Integration, IntegrationAuthType
from app.services import integration_broker


def test_store_secret_creates_new_secret_and_version():
    mock_client = MagicMock()
    mock_client.create_secret.return_value = MagicMock(name="projects/p/secrets/s")
    mock_client.create_secret.return_value.name = "projects/p/secrets/s"
    mock_client.add_secret_version.return_value = MagicMock(name="projects/p/secrets/s/versions/1")
    mock_client.add_secret_version.return_value.name = "projects/p/secrets/s/versions/1"

    with patch.object(integration_broker, "_secret_client", return_value=mock_client):
        result = integration_broker.store_secret("p", "s", "super-secret-value")

    assert result == "projects/p/secrets/s/versions/1"
    mock_client.create_secret.assert_called_once()
    # the raw value only ever reaches add_secret_version's payload, nothing else
    payload = mock_client.add_secret_version.call_args.kwargs["payload"]
    assert payload["data"] == b"super-secret-value"


def test_store_secret_adds_version_when_secret_already_exists():
    mock_client = MagicMock()
    mock_client.create_secret.side_effect = AlreadyExists("already exists")
    mock_client.add_secret_version.return_value = MagicMock(name="projects/p/secrets/s/versions/2")
    mock_client.add_secret_version.return_value.name = "projects/p/secrets/s/versions/2"

    with patch.object(integration_broker, "_secret_client", return_value=mock_client):
        result = integration_broker.store_secret("p", "s", "rotated-value")

    assert result == "projects/p/secrets/s/versions/2"
    assert mock_client.add_secret_version.call_args.kwargs["parent"] == "projects/p/secrets/s"


async def test_call_integration_raises_for_unknown_integration():
    with patch("app.services.integration_broker.store.get_integration", return_value=None):
        with pytest.raises(ValueError, match="no integration"):
            await integration_broker.call_integration("org-test", "integ-1", "GET", "/x")


async def test_call_integration_raises_for_disabled_integration():
    disabled = Integration(
        id="integ-1", kind="slack", base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.BEARER, secret_ref="ref", enabled=False,
    )
    with patch("app.services.integration_broker.store.get_integration", return_value=disabled):
        with pytest.raises(ValueError, match="disabled"):
            await integration_broker.call_integration("org-test", "integ-1", "GET", "/x")


async def test_call_integration_attaches_bearer_auth_header():
    enabled = Integration(
        id="integ-1", kind="slack", base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.BEARER, secret_ref="ref", enabled=True,
    )
    fake_response = httpx.Response(200, json={"ok": True})

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.request = AsyncMock(return_value=fake_response)

    with (
        patch("app.services.integration_broker.store.get_integration", return_value=enabled),
        patch.object(integration_broker, "_resolve_secret", return_value="xoxb-fake-token"),
        patch("app.services.integration_broker.httpx.AsyncClient", return_value=mock_async_client),
    ):
        response = await integration_broker.call_integration("org-test", "integ-1", "POST", "/chat.postMessage")

    assert response.status_code == 200
    call_kwargs = mock_async_client.__aenter__.return_value.request.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer xoxb-fake-token"
