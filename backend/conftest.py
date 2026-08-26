import os
from unittest.mock import patch

import pytest

# Settings requires this to construct even when a test never touches a real
# Firestore/Pub-Sub client (they're all mocked in unit tests).
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "corporate-test")


@pytest.fixture(autouse=True)
def _default_unpaused_agent():
    """audited_task's wrapper (departments/base.py) and the CEO branch of
    handle_agent_turn (app/services/dispatch.py) both call store.get_agent to
    check Agent.paused before doing any work — real network call otherwise.
    None (agent not found) is a safe default: both call sites treat that the
    same as "not paused". Tests that actually exercise pause behavior
    (tests/test_department_pause_guard.py, the pause/resume cases in
    tests/test_org_api.py) override this locally with their own patch."""
    with patch("app.services.store.get_agent", return_value=None):
        yield


@pytest.fixture(autouse=True)
def _bypass_org_auth():
    """API tests exercise route logic, not the auth layer itself (that has
    its own dedicated tests/test_auth.py) — override the require_org_member
    and require_internal_oidc dependencies FastAPI-style so tests don't need
    to fabricate a real Firebase ID token or Google-signed OIDC token."""
    from app.main import app
    from app.services.auth import AuthenticatedUser, require_internal_oidc, require_org_member

    app.dependency_overrides[require_org_member] = lambda: AuthenticatedUser(uid="test-uid", email="test@example.com")
    app.dependency_overrides[require_internal_oidc] = lambda: None
    yield
    app.dependency_overrides.pop(require_org_member, None)
    app.dependency_overrides.pop(require_internal_oidc, None)
