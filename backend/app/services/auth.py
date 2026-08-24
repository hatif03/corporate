"""Firebase Auth verification + org membership checks — defense in depth
per docs/system_prompt.md: a Firestore Security Rule alone isn't enough
once the backend itself writes with an elevated service account, so the
backend independently verifies both the caller's identity AND their
membership in the org they're trying to act on.

Every /api/org/{org_id}/* router is wired with require_org_member as a
router-level dependency (see app/main.py) — not per-endpoint, so a new
endpoint added to an existing router can't accidentally skip auth.
/internal/* routes use require_pubsub_push instead: end-user Firebase ID
tokens and Pub/Sub's OIDC push tokens are different credential types, and
the backend is deployed --allow-unauthenticated (see app/api/internal.py's
module docstring for why Cloud Run's own IAM gate can't do this instead).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import firebase_admin
from fastapi import Header, HTTPException, Request
from firebase_admin import auth
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings
from app.services import store

_PUBSUB_PUSH_SERVICE_ACCOUNT = f"corporate-backend-sa@{settings.google_cloud_project}.iam.gserviceaccount.com"


@dataclass
class AuthenticatedUser:
    uid: str
    email: str | None


@lru_cache
def _ensure_app() -> None:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed Authorization header")
    return authorization.removeprefix("Bearer ").strip()


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    _ensure_app()
    token = _extract_bearer_token(authorization)
    try:
        decoded = auth.verify_id_token(token)
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError) as exc:
        raise HTTPException(status_code=401, detail=f"invalid ID token: {exc}") from None
    return AuthenticatedUser(uid=decoded["uid"], email=decoded.get("email"))


async def require_org_member(org_id: str, authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """Router-level dependency: verifies the Firebase ID token AND that the
    caller is a member of `org_id` — the org_id path parameter is injected
    by FastAPI the same way it is for the route handler itself."""
    user = await get_current_user(authorization)
    role = store.get_member_role(org_id, user.uid)
    if role is None:
        raise HTTPException(status_code=403, detail=f"not a member of org '{org_id}'")
    return user


async def require_internal_oidc(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Router-level dependency for every /internal/* router (Pub/Sub push
    targets in app/api/internal.py, the Cloud-Scheduler fire endpoint in
    app/api/triggers.py): verifies the Google-signed OIDC token attached to
    the request (Pub/Sub's oidc_token.service_account_email, set on the
    subscription in scripts/seed.py; Cloud Scheduler's --oidc-service-account-email
    on the job, once that's provisioned) — audience must match this exact
    request URL and the token's email must be the backend's own service
    account. This is the real access control for /internal/* now that the
    service is deployed --allow-unauthenticated (Cloud Run's own IAM gate
    can't coexist with a publicly browser-reachable /api/org/* on the same
    service)."""
    token = _extract_bearer_token(authorization)
    try:
        claims = google_id_token.verify_oauth2_token(token, google_auth_requests.Request(), audience=str(request.url))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"invalid OIDC token: {exc}") from None
    if not claims.get("email_verified") or claims.get("email") != _PUBSUB_PUSH_SERVICE_ACCOUNT:
        raise HTTPException(status_code=403, detail="OIDC token not issued to the expected push service account")


def require_role(required_role: str):
    """Factory for owner-gated actions: require_role("owner") as a
    dependency on top of require_org_member for the specific endpoints that
    need it (not every org member should be able to do everything)."""

    async def _check(org_id: str, authorization: str | None = Header(default=None)) -> AuthenticatedUser:
        user = await get_current_user(authorization)
        role = store.get_member_role(org_id, user.uid)
        if role != required_role:
            raise HTTPException(status_code=403, detail=f"requires '{required_role}' role in org '{org_id}'")
        return user

    return _check
