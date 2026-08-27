"""The only module in this codebase allowed to dereference a secret_ref to
an actual credential value. Every department tool that needs to call a
third-party API goes through call_integration() here — never holds a raw
API key/token itself. See docs/system_prompt.md's Secrets section and the
Integrations rollout list.

INTEGRATION_TEMPLATES is a declarative catalog (kind -> shape), not
per-org config — the actual Firestore Integration doc
(app/models/integration.py) references one of these kinds and supplies its
own base_url/secret_ref/auth details for that org.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import httpx
from google.api_core.exceptions import AlreadyExists
from google.cloud import secretmanager

from app.models import IntegrationAuthType
from app.services import store


@dataclass(frozen=True)
class IntegrationTemplate:
    kind: str
    default_base_url: str
    auth_type: IntegrationAuthType
    secret_label: str  # what to call the secret in the UI, e.g. "Slack Bot Token"
    docs_url: str


# Phased rollout — see docs/system_prompt.md's Integrations section for
# which department each is wired to and when.
INTEGRATION_TEMPLATES: dict[str, IntegrationTemplate] = {
    "slack": IntegrationTemplate(
        kind="slack",
        default_base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.BEARER,
        secret_label="Slack Bot Token",
        docs_url="https://api.slack.com/authentication/token-types",
    ),
    "jira": IntegrationTemplate(
        kind="jira",
        default_base_url="https://your-domain.atlassian.net/rest/api/3",
        auth_type=IntegrationAuthType.HEADER,
        secret_label="Jira API Token",
        docs_url="https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/",
    ),
    "github": IntegrationTemplate(
        kind="github",
        default_base_url="https://api.github.com",
        auth_type=IntegrationAuthType.BEARER,
        secret_label="GitHub Personal Access Token",
        docs_url="https://docs.github.com/en/rest/authentication",
    ),
    "stripe": IntegrationTemplate(
        kind="stripe",
        default_base_url="https://api.stripe.com/v1",
        auth_type=IntegrationAuthType.BEARER,
        secret_label="Stripe Secret Key",
        docs_url="https://docs.stripe.com/keys",
    ),
    "notion": IntegrationTemplate(
        kind="notion",
        default_base_url="https://api.notion.com/v1",
        auth_type=IntegrationAuthType.BEARER,
        secret_label="Notion Integration Token",
        docs_url="https://developers.notion.com/docs/authorization",
    ),
    "hubspot": IntegrationTemplate(
        kind="hubspot",
        default_base_url="https://api.hubapi.com",
        auth_type=IntegrationAuthType.BEARER,
        secret_label="HubSpot Private App Token",
        docs_url="https://developers.hubspot.com/docs/api/private-apps",
    ),
}


@lru_cache
def _secret_client() -> secretmanager.SecretManagerServiceClient:
    return secretmanager.SecretManagerServiceClient()


def _resolve_secret(secret_ref: str) -> str:
    response = _secret_client().access_secret_version(name=secret_ref)
    return response.payload.data.decode("utf-8")


def store_secret(project_id: str, secret_id: str, value: str) -> str:
    """Write-only from the caller's perspective: takes a raw secret value
    exactly once, stores it in Secret Manager, and returns only the
    resource name of the new version — the value itself is never returned,
    logged, or persisted anywhere else (see docs/system_prompt.md's Secrets
    section). secret_id should be unique per org+integration, e.g.
    "corporate-{org_id}-{integration_kind}"."""
    client = _secret_client()
    parent = f"projects/{project_id}"
    try:
        secret = client.create_secret(
            parent=parent,
            secret_id=secret_id,
            secret={"replication": {"automatic": {}}},
        )
    except AlreadyExists:
        # Re-configuring an integration — add a new version to the existing
        # secret instead of failing.
        secret_name = f"{parent}/secrets/{secret_id}"
    else:
        secret_name = secret.name

    version = client.add_secret_version(parent=secret_name, payload={"data": value.encode("utf-8")})
    return version.name


class IntegrationAccessDenied(ValueError):
    """Raised when department_id isn't in the integration's
    connected_departments allowlist. Subclasses ValueError deliberately —
    every existing call site already does `except ValueError:` fail-soft
    (notify_slack_channel, create_jira_ticket), so this needs zero changes
    there while still being distinguishable by callers that care."""


async def call_integration(
    org_id: str,
    integration_id: str,
    department_id: str,
    method: str,
    path: str,
    json: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    """Make an authenticated call to a configured third-party integration.
    Raises ValueError if the integration doesn't exist or is disabled, or
    IntegrationAccessDenied (also a ValueError) if `department_id` isn't in
    the integration's connected_departments allowlist — an empty allowlist
    (every integration's default) means unrestricted, matching pre-existing
    behavior exactly."""
    integration = store.get_integration(org_id, integration_id)
    if integration is None:
        raise ValueError(f"no integration '{integration_id}' configured for org '{org_id}'")
    if not integration.enabled:
        raise ValueError(f"integration '{integration_id}' is disabled")
    if integration.connected_departments and department_id not in integration.connected_departments:
        store.file_access_request(org_id, integration_id, department_id)
        raise IntegrationAccessDenied(
            f"department '{department_id}' doesn't have access to integration '{integration_id}' — access request filed"
        )

    headers: dict[str, str] = {}
    if integration.auth_type != IntegrationAuthType.NONE and integration.secret_ref:
        secret_value = _resolve_secret(integration.secret_ref)
        # OAUTH2 tokens (from the Connect-with-X flow, app/api/oauth.py) are
        # sent the same way a manually-pasted bearer token is — every
        # provider we support OAuth for (Slack, GitHub, Notion) expects
        # `Authorization: Bearer <token>` for its REST API regardless of how
        # the token was obtained.
        if integration.auth_type in (IntegrationAuthType.BEARER, IntegrationAuthType.OAUTH2):
            headers["Authorization"] = f"Bearer {secret_value}"
        elif integration.auth_type == IntegrationAuthType.HEADER:
            headers[integration.auth_header or "Authorization"] = secret_value

    url = f"{integration.base_url.rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        return await client.request(method, url, headers=headers, json=json, params=params)
