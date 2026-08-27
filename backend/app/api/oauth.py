""""Connect with X" OAuth flow for Slack, GitHub, and Notion — see
app/services/oauth_providers.py for the per-provider adapters and
docs/adr/0018-oauth-connect-flow.md for the research this is built on.

Two routes, deliberately outside the standard org-scoped auth:
- `/api/org/{org_id}/integrations/{kind}/oauth/start` — a plain browser
  navigation (not fetch), so it can't carry an Authorization header;
  auth is a `?token=` query param verified the same way
  require_org_member verifies one, matching app/api/voice.py's precedent.
- `/api/oauth/{kind}/callback` — called directly by the provider, never by
  our own frontend. Org identity travels in the signed `state` param
  instead of any auth header.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from firebase_admin import auth as firebase_auth

from app.config import settings
from app.models import Integration, IntegrationAuthType
from app.services import store
from app.services.auth import _ensure_app
from app.services.integration_broker import INTEGRATION_TEMPLATES, store_secret
from app.services.oauth_providers import PROVIDERS, authorize_url, exchange_code

router = APIRouter(tags=["oauth"])

_STATE_TTL_SECONDS = 600


def _frontend_url() -> str:
    # Same origin CORSMiddleware already trusts (app/main.py) — no new
    # setting needed, this is already this deployment's one real frontend.
    return f"https://{settings.google_cloud_project}.web.app"


def _redirect_uri(kind: str) -> str:
    return f"{settings.corporate_backend_url}/api/oauth/{kind}/callback"


def _sign_state(org_id: str) -> str:
    if not settings.oauth_state_secret:
        raise HTTPException(status_code=500, detail="OAuth isn't configured yet (no oauth_state_secret set)")
    payload = f"{org_id}:{int(time.time())}"
    sig = hmac.new(settings.oauth_state_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def _verify_state(state: str) -> str:
    """Returns the org_id encoded in a valid, unexpired state. Raises
    HTTPException(400) otherwise — never trusts state without checking it,
    this is the only thing stopping a forged callback from writing an
    integration into an arbitrary org."""
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        org_id, ts_str, sig = raw.rsplit(":", 2)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid state") from None
    expected = hmac.new(settings.oauth_state_secret.encode(), f"{org_id}:{ts_str}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="invalid state")
    if time.time() - int(ts_str) > _STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="state expired — try connecting again")
    return org_id


@router.get("/api/org/{org_id}/integrations/{kind}/oauth/start")
async def oauth_start(org_id: str, kind: str, token: str) -> RedirectResponse:
    if kind not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"no OAuth provider for '{kind}'")
    _ensure_app()
    try:
        decoded = firebase_auth.verify_id_token(token)
    except (
        firebase_auth.InvalidIdTokenError,
        firebase_auth.ExpiredIdTokenError,
        firebase_auth.RevokedIdTokenError,
    ):
        raise HTTPException(status_code=401, detail="invalid token") from None
    if store.get_member_role(org_id, decoded["uid"]) is None:
        raise HTTPException(status_code=403, detail=f"not a member of org '{org_id}'")

    state = _sign_state(org_id)
    return RedirectResponse(authorize_url(kind, state, _redirect_uri(kind)))


@router.get("/api/oauth/{kind}/callback")
async def oauth_callback(kind: str, request: Request) -> RedirectResponse:
    if kind not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"no OAuth provider for '{kind}'")

    error = request.query_params.get("error")
    if error:
        return RedirectResponse(f"{_frontend_url()}/?oauth_error={error}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code/state")

    org_id = _verify_state(state)
    access_token = await exchange_code(kind, code, _redirect_uri(kind))

    integration_id = f"integ-{kind}-oauth"
    secret_ref = store_secret(settings.google_cloud_project, f"corporate-{org_id}-{integration_id}", access_token)

    template = INTEGRATION_TEMPLATES[kind]
    existing = store.get_integration(org_id, integration_id)
    integration = Integration(
        id=integration_id,
        kind=kind,
        base_url=template.default_base_url,
        auth_type=IntegrationAuthType.OAUTH2,
        secret_ref=secret_ref,
        connected_departments=existing.connected_departments if existing else [],
    )
    store.create_integration(org_id, integration)

    return RedirectResponse(_frontend_url())
