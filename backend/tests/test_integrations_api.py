from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_catalog_lists_known_kinds():
    response = client.get("/api/org/demo/integrations/catalog")
    assert response.status_code == 200
    body = response.json()
    assert "slack" in body
    assert body["slack"]["secret_label"] == "Slack Bot Token"


def test_create_integration_requires_secret_for_bearer_kind():
    response = client.post("/api/org/demo/integrations", json={"kind": "slack"})
    assert response.status_code == 400


def test_create_integration_never_returns_secret_ref():
    with (
        patch("app.api.integrations.store_secret", return_value="projects/p/secrets/s/versions/1") as mock_store,
        patch("app.api.integrations.store.create_integration") as mock_create,
    ):
        response = client.post(
            "/api/org/demo/integrations",
            json={"kind": "slack", "secret_value": "xoxb-real-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "secretRef" not in body
    assert "secret_ref" not in body
    assert mock_store.call_args.args[2] == "xoxb-real-token"
    assert mock_create.called


def test_create_integration_rejects_unknown_kind():
    response = client.post("/api/org/demo/integrations", json={"kind": "not-a-real-thing"})
    assert response.status_code == 400
