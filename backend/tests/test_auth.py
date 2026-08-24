from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from app.main import app
from app.services.auth import get_current_user, require_internal_oidc, require_org_member


async def test_get_current_user_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


async def test_get_current_user_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization="NotBearer abc123")
    assert exc_info.value.status_code == 401


async def test_get_current_user_accepts_valid_token():
    with (
        patch("app.services.auth._ensure_app"),
        patch("app.services.auth.auth.verify_id_token", return_value={"uid": "u1", "email": "a@b.com"}),
    ):
        user = await get_current_user(authorization="Bearer valid-token")

    assert user.uid == "u1"
    assert user.email == "a@b.com"


async def test_get_current_user_rejects_invalid_token():
    with (
        patch("app.services.auth._ensure_app"),
        patch(
            "app.services.auth.auth.verify_id_token",
            side_effect=firebase_auth.InvalidIdTokenError("bad token"),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer bad-token")

    assert exc_info.value.status_code == 401


async def test_require_org_member_rejects_non_member():
    with (
        patch("app.services.auth._ensure_app"),
        patch("app.services.auth.auth.verify_id_token", return_value={"uid": "u1", "email": None}),
        patch("app.services.auth.store.get_member_role", return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_org_member("some-org", authorization="Bearer valid-token")

    assert exc_info.value.status_code == 403


async def test_require_org_member_accepts_member():
    with (
        patch("app.services.auth._ensure_app"),
        patch("app.services.auth.auth.verify_id_token", return_value={"uid": "u1", "email": None}),
        patch("app.services.auth.store.get_member_role", return_value="owner"),
    ):
        user = await require_org_member("some-org", authorization="Bearer valid-token")

    assert user.uid == "u1"


async def test_require_internal_oidc_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        await require_internal_oidc(request=None, authorization=None)
    assert exc_info.value.status_code == 401


def _fake_request() -> MagicMock:
    return MagicMock(url="https://corporate-backend.example/internal/agent-turn/ceo")


async def test_require_internal_oidc_rejects_invalid_token():
    with patch("app.services.auth.google_id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
        with pytest.raises(HTTPException) as exc_info:
            await require_internal_oidc(request=_fake_request(), authorization="Bearer bad-token")
    assert exc_info.value.status_code == 401


async def test_require_internal_oidc_rejects_wrong_service_account():
    claims = {"email_verified": True, "email": "someone-else@corporate-test.iam.gserviceaccount.com"}
    with patch("app.services.auth.google_id_token.verify_oauth2_token", return_value=claims):
        with pytest.raises(HTTPException) as exc_info:
            await require_internal_oidc(request=_fake_request(), authorization="Bearer valid-token")
    assert exc_info.value.status_code == 403


async def test_require_internal_oidc_accepts_backend_service_account():
    claims = {"email_verified": True, "email": "corporate-backend-sa@corporate-test.iam.gserviceaccount.com"}
    with patch("app.services.auth.google_id_token.verify_oauth2_token", return_value=claims):
        result = await require_internal_oidc(request=_fake_request(), authorization="Bearer valid-token")
    assert result is None


def test_org_scoped_endpoint_actually_rejects_unauthenticated_requests():
    """The conftest.py autouse fixture overrides require_org_member for
    every other test in this suite — that only proves the dependency is
    override-able, not that it's genuinely enforced. This test removes the
    override to prove an unauthenticated request to a real /api/org/*
    route is actually rejected, not silently let through."""
    app.dependency_overrides.pop(require_org_member, None)
    try:
        client = TestClient(app)
        response = client.get("/api/org/demo/integrations/catalog")
        assert response.status_code == 401
    finally:
        # restore for any tests that run after this one in the same session
        from app.services.auth import AuthenticatedUser

        app.dependency_overrides[require_org_member] = lambda: AuthenticatedUser(
            uid="test-uid", email="test@example.com"
        )


def test_internal_endpoint_actually_rejects_unauthenticated_requests():
    """Same proof as above, for require_internal_oidc: conftest.py's autouse
    override only shows the dependency is override-able, not enforced."""
    app.dependency_overrides.pop(require_internal_oidc, None)
    try:
        client = TestClient(app)
        response = client.post("/internal/agent-turn/ceo", json={"message": {"data": ""}})
        assert response.status_code == 401
    finally:
        app.dependency_overrides[require_internal_oidc] = lambda: None
