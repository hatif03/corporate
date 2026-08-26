from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.access_requests import require_owner
from app.main import app
from app.models import AccessRequest, AccessRequestStatus, Integration, IntegrationAuthType
from app.services.auth import AuthenticatedUser

client = TestClient(app)


def test_list_requests_returns_store_contents():
    requests = [AccessRequest(id="areq-1", integration_id="integ-1", department_id="sales_crm")]
    with patch("app.api.access_requests.store.list_access_requests", return_value=requests):
        response = client.get("/api/org/demo/access_requests")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "areq-1"


def test_resolve_requires_owner_role():
    # _bypass_org_auth (conftest) only overrides require_org_member, not the
    # separate owner-gated dependency — resolve_request should still 403
    # under the real require_owner check for a non-owner caller.
    with patch("app.services.store.get_member_role", return_value="member"):
        response = client.post("/api/org/demo/access_requests/areq-1/resolve?approve=true")
    assert response.status_code in (401, 403)


def test_resolve_approve_appends_department_and_updates_status():
    request = AccessRequest(id="areq-1", integration_id="integ-1", department_id="sales_crm")
    integration = Integration(
        id="integ-1", kind="slack", base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.BEARER, secret_ref="ref", connected_departments=["engineering_sre"],
    )
    app.dependency_overrides[require_owner] = lambda: AuthenticatedUser(uid="owner-uid", email="o@example.com")
    try:
        with (
            patch("app.api.access_requests.store.list_access_requests", return_value=[request]),
            patch("app.api.access_requests.store.resolve_access_request") as mock_resolve,
            patch("app.api.access_requests.store.get_integration", return_value=integration),
            patch("app.api.access_requests.store.set_integration_departments") as mock_set_depts,
        ):
            response = client.post("/api/org/demo/access_requests/areq-1/resolve?approve=true")
    finally:
        app.dependency_overrides.pop(require_owner, None)

    assert response.status_code == 200
    assert response.json()["status"] == AccessRequestStatus.APPROVED.value
    mock_resolve.assert_called_once()
    mock_set_depts.assert_called_once_with("demo", "integ-1", ["engineering_sre", "sales_crm"])


def test_resolve_unknown_request_404s():
    app.dependency_overrides[require_owner] = lambda: AuthenticatedUser(uid="owner-uid", email="o@example.com")
    try:
        with patch("app.api.access_requests.store.list_access_requests", return_value=[]):
            response = client.post("/api/org/demo/access_requests/areq-missing/resolve?approve=true")
    finally:
        app.dependency_overrides.pop(require_owner, None)

    assert response.status_code == 404
