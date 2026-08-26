"""Standing queue of department access requests filed by call_integration
on denial (app/services/integration_broker.py) — an org-admin-timescale
governance decision, not a per-task blocker. See docs/system_prompt.md's
Integrations section."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models import AccessRequestStatus
from app.services import store
from app.services.auth import AuthenticatedUser, require_role

router = APIRouter(prefix="/api/org/{org_id}/access_requests", tags=["access_requests"])

# A module-level singleton (not require_role("owner") inlined in the route
# signature) so tests can target this exact dependency object via FastAPI's
# app.dependency_overrides, which keys on callable identity — a fresh
# require_role("owner") call produces a distinct closure every time.
require_owner = require_role("owner")


@router.get("")
async def list_requests(org_id: str) -> list[dict]:
    return [r.model_dump(mode="json", by_alias=True) for r in store.list_access_requests(org_id)]


@router.post("/{request_id}/resolve")
async def resolve_request(
    org_id: str, request_id: str, approve: bool, user: AuthenticatedUser = Depends(require_owner)
) -> dict:
    requests = {r.id: r for r in store.list_access_requests(org_id)}
    request = requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"no access request '{request_id}'")

    status = AccessRequestStatus.APPROVED if approve else AccessRequestStatus.DENIED
    store.resolve_access_request(org_id, request_id, status, resolved_by=user.uid)

    if approve:
        integration = store.get_integration(org_id, request.integration_id)
        if integration is not None and request.department_id not in integration.connected_departments:
            store.set_integration_departments(
                org_id, request.integration_id, [*integration.connected_departments, request.department_id]
            )

    return {"status": status.value}
