from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import store

router = APIRouter(prefix="/api/org/{org_id}/agents", tags=["agents"])


class UpdatePersonaRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    character: str | None = None
    accent_color: str | None = None


@router.post("/{agent_id}/pause")
async def pause(org_id: str, agent_id: str) -> dict:
    if store.get_agent(org_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    store.set_agent_paused(org_id, agent_id, True)
    return {"paused": True}


@router.post("/{agent_id}/resume")
async def resume(org_id: str, agent_id: str) -> dict:
    if store.get_agent(org_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    store.set_agent_paused(org_id, agent_id, False)
    return {"paused": False}


@router.patch("/{agent_id}")
async def update_persona(org_id: str, agent_id: str, body: UpdatePersonaRequest) -> dict:
    """Lets an org customize an existing agent's persona (name/bio/sprite/
    accent) — not a "create a new department" flow, which still requires
    real code via the new-department skill."""
    if store.get_agent(org_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    fields = body.model_dump(exclude_none=True)
    if fields:
        store.update_agent_persona(org_id, agent_id, **fields)
    updated = store.get_agent(org_id, agent_id)
    return updated.model_dump(mode="json", by_alias=True)
