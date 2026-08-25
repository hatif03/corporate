"""Confirms the Sales & CRM A2A server (app/a2a_server.py) actually serves a
valid Agent Card — the external-boundary exposure from ADR-0004. This is
the "A2A gate" check from the plan's verification section: fetch
/.well-known/agent-card.json and confirm the protocol surface is live."""

import warnings

from starlette.testclient import TestClient


def test_agent_card_is_served_and_describes_the_sales_pipeline():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from app.a2a_server import app

    with TestClient(app) as client:
        response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    # _flash suffix is real: external A2A callers always get the flash-tier
    # pipeline singleton, never model_tier="pro" (ADR-0013) — see
    # departments/sales_crm/__init__.py's root_agent.
    assert card["name"] == "sales_crm_pipeline_flash"
    assert "skills" in card and len(card["skills"]) > 0
    assert card["capabilities"]["streaming"] is False
