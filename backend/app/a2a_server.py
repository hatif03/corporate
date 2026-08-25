"""Standalone A2A server for the Sales & CRM department — the ONE external
front door this project exposes (ADR-0004). Deployed as its own Cloud Run
service, separate from the main backend, so the A2A well-known discovery
route (`/.well-known/agent-card.json`) sits at this service's own root as
the A2A spec expects, rather than under a path prefix.

Run locally with: uvicorn app.a2a_server:app --port 8001
Deploy with the same `gcloud run deploy` pattern as the main backend (see
README.md) but pointed at this module and a separate service name, e.g.
`corporate-a2a-sales`.

Internally the Sales pipeline still talks to the same Firestore-backed
session service as everything else (see FirestoreSessionService in
app/services/session_service.py) — this is a second entrypoint onto the
same agent, not a separate copy of it.
"""

from __future__ import annotations

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.runners import Runner

from app.config import settings
from app.services.session_service import FirestoreSessionService
from departments.sales_crm.agents import sales_pipeline

_runner = Runner(
    agent=sales_pipeline,
    session_service=FirestoreSessionService(),
    app_name="corporate",
    auto_create_session=True,
)

_public_url = settings.corporate_a2a_sales_url
_host = _public_url.replace("https://", "").replace("http://", "").rstrip("/") or "localhost"
_protocol = "https" if _public_url.startswith("https") else "http"
# to_a2a always bakes a literal ":{port}" into the advertised agent-card URL
# (f"{protocol}://{host}:{port}/", no default-port omission) — 443 is the
# real public port Cloud Run serves HTTPS on, so this is the port that makes
# the advertised URL actually reachable, not the container's internal
# uvicorn --port (see deploy.sh), which callers never talk to directly.
_public_port = 443 if _protocol == "https" else 8001

app = to_a2a(
    sales_pipeline,
    host=_host,
    port=_public_port,
    protocol=_protocol,
    runner=_runner,
)
