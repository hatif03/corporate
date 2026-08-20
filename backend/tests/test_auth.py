from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from app.main import app
from app.services.auth import get_current_user, require_org_member


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
