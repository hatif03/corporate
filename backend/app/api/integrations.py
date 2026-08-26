"""Integration setup — write-only for secrets. See
app/services/integration_broker.py's module docstring and
docs/system_prompt.md's Secrets section: a raw secret value only ever
passes through this one POST body, gets written straight to Secret
Manager, and is never stored in Firestore or returned in any response."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.models import Integration, IntegrationAuthType
from app.services import store
from app.services.integration_broker import INTEGRATION_TEMPLATES, store_secret

router = APIRouter(prefix="/api/org/{org_id}/integrations", tags=["integrations"])


class CreateIntegrationRequest(BaseModel):
    kind: str
    base_url: str | None = None
    auth_header: str | None = None
    secret_value: str | None = None
    connected_departments: list[str] = []


@router.get("")
async def list_integrations(org_id: str) -> list[dict]:
    """Every integration configured for this org, public fields only —
    backs the frontend's "Connected apps" panel (Settings tab)."""
    return [i.model_dump(mode="json", by_alias=True, exclude={"secret_ref"}) for i in store.list_integrations(org_id)]


@router.get("/catalog")
async def catalog() -> dict:
    """The declarative template catalog — what kinds exist and what each needs."""
    return {
        kind: {
            "default_base_url": t.default_base_url,
            "auth_type": t.auth_type.value,
            "secret_label": t.secret_label,
            "docs_url": t.docs_url,
        }
        for kind, t in INTEGRATION_TEMPLATES.items()
    }


@router.post("")
async def create_integration(org_id: str, body: CreateIntegrationRequest) -> dict:
    template = INTEGRATION_TEMPLATES.get(body.kind)
    if template is None:
        raise HTTPException(status_code=400, detail=f"unknown integration kind '{body.kind}'")

    integration_id = f"integ-{uuid.uuid4().hex[:10]}"
    secret_ref = None
    if template.auth_type != IntegrationAuthType.NONE:
        if not body.secret_value:
            raise HTTPException(status_code=400, detail=f"'{body.kind}' requires a secret_value ({template.secret_label})")
        secret_ref = store_secret(
            settings.google_cloud_project, f"corporate-{org_id}-{integration_id}", body.secret_value
        )

    integration = Integration(
        id=integration_id,
        kind=body.kind,
        base_url=body.base_url or template.default_base_url,
        auth_type=template.auth_type,
        auth_header=body.auth_header,
        secret_ref=secret_ref,
        connected_departments=body.connected_departments,
    )
    store.create_integration(org_id, integration)
    # Never echo secret_ref/secret_value back — the response is the
    # integration's public config only.
    return integration.model_dump(mode="json", by_alias=True, exclude={"secret_ref"})


@router.post("/{integration_id}/toggle")
async def toggle_integration(org_id: str, integration_id: str, enabled: bool) -> dict:
    store.set_integration_enabled(org_id, integration_id, enabled)
    return {"enabled": enabled}


class UpdateDepartmentsRequest(BaseModel):
    connected_departments: list[str]


@router.post("/{integration_id}/departments")
async def update_departments(org_id: str, integration_id: str, body: UpdateDepartmentsRequest) -> dict:
    """Sets which departments may call this integration — empty means
    unrestricted (see IntegrationAccessDenied in integration_broker.py)."""
    store.set_integration_departments(org_id, integration_id, body.connected_departments)
    return {"connected_departments": body.connected_departments}
