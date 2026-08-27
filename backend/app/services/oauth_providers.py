"""Per-provider OAuth adapters for the "Connect with X" flow
(app/api/oauth.py) — authorize-URL construction and the code-for-token
exchange. Each provider's transport genuinely differs (confirmed against
real current provider docs, not assumed): Slack and GitHub exchange via a
form POST with client_secret as a form field; Notion exchanges via a JSON
body with client_secret as HTTP Basic Auth. No single generic OAuth helper
covers all three, so each is its own small branch rather than a forced
abstraction. See docs/adr/0018-oauth-connect-flow.md.

Every provider needs a real app registered in its own developer console
first (client_id/client_secret, a pre-registered exact redirect URL) —
this module has no way to create that, it's a one-time manual prerequisite.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.services.integration_broker import _resolve_secret


@dataclass(frozen=True)
class OAuthProvider:
    kind: str
    client_id: str
    authorize_base: str
    scope: str
    extra_authorize_params: dict[str, str]


PROVIDERS: dict[str, OAuthProvider] = {
    "slack": OAuthProvider(
        kind="slack",
        client_id=settings.slack_oauth_client_id,
        authorize_base="https://slack.com/oauth/v2/authorize",
        scope="chat:write,chat:write.public",
        extra_authorize_params={},
    ),
    "github": OAuthProvider(
        kind="github",
        client_id=settings.github_oauth_client_id,
        authorize_base="https://github.com/login/oauth/authorize",
        scope="repo",
        extra_authorize_params={},
    ),
    "notion": OAuthProvider(
        kind="notion",
        client_id=settings.notion_oauth_client_id,
        authorize_base="https://api.notion.com/v1/oauth/authorize",
        scope="",
        # Notion has no OAuth `scope` param — access is granted per-page via
        # the user's own page-picker at authorization time; `owner=user` is
        # a fixed literal Notion's API requires.
        extra_authorize_params={"owner": "user", "response_type": "code"},
    ),
}


def _client_secret(kind: str) -> str:
    return _resolve_secret(f"projects/{settings.google_cloud_project}/secrets/oauth-{kind}-client-secret/versions/latest")


def authorize_url(kind: str, state: str, redirect_uri: str) -> str:
    provider = PROVIDERS[kind]
    params = {"client_id": provider.client_id, "redirect_uri": redirect_uri, "state": state, **provider.extra_authorize_params}
    if provider.scope:
        params["scope"] = provider.scope
    return f"{provider.authorize_base}?{urlencode(params)}"


async def exchange_code(kind: str, code: str, redirect_uri: str) -> str:
    """Exchanges an authorization code for an access token. Returns the
    token. Raises ValueError if the provider's own response indicates
    failure."""
    secret = _client_secret(kind)
    async with httpx.AsyncClient() as client:
        if kind == "slack":
            resp = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={"code": code, "client_id": PROVIDERS["slack"].client_id, "client_secret": secret, "redirect_uri": redirect_uri},
            )
            data = resp.json()
            if not data.get("ok"):
                raise ValueError(f"slack oauth exchange failed: {data.get('error')}")
            return data["access_token"]

        if kind == "github":
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={"client_id": PROVIDERS["github"].client_id, "client_secret": secret, "code": code, "redirect_uri": redirect_uri},
                headers={"Accept": "application/json"},
            )
            data = resp.json()
            if "access_token" not in data:
                raise ValueError(f"github oauth exchange failed: {data.get('error_description', data)}")
            return data["access_token"]

        if kind == "notion":
            resp = await client.post(
                "https://api.notion.com/v1/oauth/token",
                json={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
                auth=httpx.BasicAuth(PROVIDERS["notion"].client_id, secret),
            )
            data = resp.json()
            if "access_token" not in data:
                raise ValueError(f"notion oauth exchange failed: {data}")
            return data["access_token"]

        raise ValueError(f"unknown OAuth provider '{kind}'")
