from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import store

router = APIRouter(prefix="/api/org/{org_id}/agents", tags=["agents"])


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
