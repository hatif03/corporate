import os

import pytest

# Settings requires this to construct even when a test never touches a real
# Firestore/Pub-Sub client (they're all mocked in unit tests).
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "corporate-test")


@pytest.fixture(autouse=True)
def _bypass_org_auth():
    """API tests exercise route logic, not the auth layer itself (that has
    its own dedicated tests/test_auth.py) — override the require_org_member
    dependency FastAPI-style so every /api/org/* test doesn't need to
    fabricate a real Firebase ID token."""
    from app.main import app
    from app.services.auth import AuthenticatedUser, require_org_member

    app.dependency_overrides[require_org_member] = lambda: AuthenticatedUser(uid="test-uid", email="test@example.com")
    yield
    app.dependency_overrides.pop(require_org_member, None)
