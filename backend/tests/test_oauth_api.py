import dataclasses
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from firebase_admin import auth as firebase_auth

from app.api import oauth
from app.main import app
from app.models import Integration, IntegrationAuthType

client = TestClient(app)


def test_state_sign_and_verify_roundtrip():
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        state = oauth._sign_state("demo")
        assert oauth._verify_state(state) == "demo"


def test_state_verify_rejects_tampered_signature():
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        state = oauth._sign_state("demo")
    tampered = state[:-4] + "xxxx"
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        with pytest.raises(Exception):
            oauth._verify_state(tampered)


def test_state_verify_rejects_expired_state():
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"), patch("app.api.oauth.time.time", return_value=1000):
        state = oauth._sign_state("demo")
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"), patch("app.api.oauth.time.time", return_value=1000 + oauth._STATE_TTL_SECONDS + 1):
        with pytest.raises(Exception):
            oauth._verify_state(state)


def test_oauth_start_unknown_provider_404s():
    response = client.get("/api/org/demo/integrations/not-a-real-kind/oauth/start?token=x")
    assert response.status_code == 404


def test_oauth_start_rejects_invalid_token():
    with patch("app.api.oauth.firebase_auth.verify_id_token", side_effect=firebase_auth.InvalidIdTokenError("bad token")):
        response = client.get("/api/org/demo/integrations/slack/oauth/start?token=bad", follow_redirects=False)
    assert response.status_code == 401


def test_oauth_start_rejects_non_member():
    with (
        patch("app.api.oauth.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.oauth.store.get_member_role", return_value=None),
    ):
        response = client.get("/api/org/demo/integrations/slack/oauth/start?token=valid", follow_redirects=False)
    assert response.status_code == 403


def test_oauth_start_redirects_member_to_provider():
    configured_slack = dataclasses.replace(oauth.PROVIDERS["slack"], client_id="test-client-id")
    with (
        patch("app.api.oauth.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.oauth.store.get_member_role", return_value="owner"),
        patch.object(oauth.settings, "oauth_state_secret", "test-secret"),
        patch.dict(oauth.PROVIDERS, {"slack": configured_slack}),
    ):
        response = client.get("/api/org/demo/integrations/slack/oauth/start?token=valid", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "slack.com/oauth/v2/authorize" in response.headers["location"]


def test_oauth_start_redirects_to_frontend_with_error_when_state_secret_missing():
    configured_slack = dataclasses.replace(oauth.PROVIDERS["slack"], client_id="test-client-id")
    with (
        patch("app.api.oauth.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.oauth.store.get_member_role", return_value="owner"),
        patch.object(oauth.settings, "oauth_state_secret", ""),
        patch.dict(oauth.PROVIDERS, {"slack": configured_slack}),
    ):
        response = client.get("/api/org/demo/integrations/slack/oauth/start?token=valid", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "oauth_error=not_configured" in response.headers["location"]
    assert ".web.app" in response.headers["location"]


def test_oauth_start_redirects_to_frontend_with_error_when_client_id_missing():
    unconfigured_slack = dataclasses.replace(oauth.PROVIDERS["slack"], client_id="")
    with (
        patch("app.api.oauth.firebase_auth.verify_id_token", return_value={"uid": "uid-1"}),
        patch("app.api.oauth.store.get_member_role", return_value="owner"),
        patch.object(oauth.settings, "oauth_state_secret", "test-secret"),
        patch.dict(oauth.PROVIDERS, {"slack": unconfigured_slack}),
    ):
        response = client.get("/api/org/demo/integrations/slack/oauth/start?token=valid", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "oauth_error=not_configured" in response.headers["location"]


def test_oauth_callback_missing_code_400s():
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        response = client.get("/api/oauth/slack/callback", follow_redirects=False)
    assert response.status_code == 400


def test_oauth_callback_provider_error_redirects_with_query_param():
    response = client.get("/api/oauth/slack/callback?error=access_denied", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "oauth_error=access_denied" in response.headers["location"]


def test_oauth_callback_exchanges_code_and_creates_integration():
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        state = oauth._sign_state("demo")

    with (
        patch.object(oauth.settings, "oauth_state_secret", "test-secret"),
        patch("app.api.oauth.exchange_code", return_value="xoxb-fake-token") as mock_exchange,
        patch("app.api.oauth.store_secret", return_value="projects/p/secrets/s/versions/1") as mock_store_secret,
        patch("app.api.oauth.store.get_integration", return_value=None),
        patch("app.api.oauth.store.create_integration") as mock_create,
    ):
        response = client.get(f"/api/oauth/slack/callback?code=abc123&state={state}", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert mock_exchange.called
    assert mock_store_secret.call_args.args[2] == "xoxb-fake-token"
    created_integration = mock_create.call_args.args[1]
    assert isinstance(created_integration, Integration)
    assert created_integration.kind == "slack"
    assert created_integration.auth_type == IntegrationAuthType.OAUTH2


def test_oauth_callback_exchange_failure_redirects_with_error_not_a_500():
    """A failed exchange_code/store_secret call previously dead-ended a real
    user on a raw 500 mid-OAuth-flow with no way back to the app — see
    ADR-0019's Part 4. Must redirect with ?oauth_error=, same as the
    provider-declared-error branch."""
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        state = oauth._sign_state("demo")

    with (
        patch.object(oauth.settings, "oauth_state_secret", "test-secret"),
        patch("app.api.oauth.exchange_code", side_effect=ValueError("slack oauth exchange failed: invalid_grant")),
    ):
        response = client.get(f"/api/oauth/slack/callback?code=abc123&state={state}", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert "oauth_error=exchange_failed" in response.headers["location"]


def test_oauth_callback_preserves_existing_connected_departments():
    existing = Integration(
        id="integ-slack-oauth", kind="slack", base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.OAUTH2, connected_departments=["engineering_sre"],
    )
    with patch.object(oauth.settings, "oauth_state_secret", "test-secret"):
        state = oauth._sign_state("demo")

    with (
        patch.object(oauth.settings, "oauth_state_secret", "test-secret"),
        patch("app.api.oauth.exchange_code", return_value="xoxb-fake-token"),
        patch("app.api.oauth.store_secret", return_value="projects/p/secrets/s/versions/1"),
        patch("app.api.oauth.store.get_integration", return_value=existing),
        patch("app.api.oauth.store.create_integration") as mock_create,
    ):
        client.get(f"/api/oauth/slack/callback?code=abc123&state={state}", follow_redirects=False)

    created_integration = mock_create.call_args.args[1]
    assert created_integration.connected_departments == ["engineering_sre"]
