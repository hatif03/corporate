"""The global exception handler and enriched /api/healthz (app/main.py) —
confirmed real gaps this session's production audit found: only department
task processing got failure containment (@audited_task), every other route
had none, falling through to Starlette's bare default 500 on any unhandled
error. See also the per-service tests for the specific fixes this enabled
(oauth callback redirect, integration_broker/veo_client error handling)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
# Starlette's TestClient re-raises unhandled server exceptions by default
# (so a test author notices a route crashed) instead of returning the
# registered exception handler's response — exactly what these two tests
# need to observe, so they need raise_server_exceptions=False.
client_no_raise = TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_clean_500_not_a_stack_trace():
    with patch("app.api.org.store.get_org_settings", side_effect=RuntimeError("firestore is down")):
        response = client_no_raise.get("/api/org/demo/settings")

    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
    # The real exception text must never leak to the client.
    assert "firestore is down" not in response.text


def test_unhandled_exception_logs_activity_for_the_org_in_the_path():
    with (
        patch("app.api.org.store.get_org_settings", side_effect=RuntimeError("firestore is down")),
        patch("app.services.store.log_activity") as mock_log,
    ):
        client_no_raise.get("/api/org/demo/settings")

    mock_log.assert_called_once()
    assert mock_log.call_args.args[0] == "demo"
    assert mock_log.call_args.args[1] == "backend"
    assert "firestore is down" in mock_log.call_args.args[3]


def test_deliberate_http_exception_is_not_swallowed_by_the_global_handler():
    """A route that deliberately raises HTTPException (a normal 4xx) must
    keep behaving normally — the global Exception handler must not shadow
    FastAPI's own more-specific HTTPException handling."""
    response = client.post("/api/org/demo/settings", json={"daily_gemini_call_limit": 0})
    assert response.status_code == 400


def test_healthz_reports_ok_when_firestore_is_reachable():
    with patch("app.main.store.get_org_settings"):
        response = client.get("/api/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["firestore"] == "ok"


def test_healthz_reports_degraded_when_firestore_call_fails():
    with patch("app.main.store.get_org_settings", side_effect=RuntimeError("connection refused")):
        response = client.get("/api/healthz")

    assert response.status_code == 200  # the health check itself must not 500
    body = response.json()
    assert body["status"] == "degraded"
    assert "connection refused" in body["firestore"]
