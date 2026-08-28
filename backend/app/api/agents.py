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


class AddSkillRequest(BaseModel):
    title: str
    instructions: str


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


@router.get("/{agent_id}/skills")
async def list_skills(org_id: str, agent_id: str) -> list[dict]:
    return store.list_agent_custom_skills(org_id, agent_id)


@router.post("/{agent_id}/skills")
async def add_skill(org_id: str, agent_id: str, body: AddSkillRequest) -> dict:
    """Org-added guidance for this one agent — see
    shared/custom_skills.py for how it reaches the agent's actual turns."""
    if store.get_agent(org_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    skill_id = store.add_agent_custom_skill(org_id, agent_id, body.title, body.instructions)
    return {"id": skill_id, "title": body.title, "instructions": body.instructions}


@router.delete("/{agent_id}/skills/{skill_id}")
async def delete_skill(org_id: str, agent_id: str, skill_id: str) -> dict:
    """Also how a pending (agent-proposed) skill gets rejected — just deletes it."""
    store.delete_agent_custom_skill(org_id, agent_id, skill_id)
    return {"deleted": True}


@router.post("/{agent_id}/skills/{skill_id}/approve")
async def approve_skill(org_id: str, agent_id: str, skill_id: str) -> dict:
    """Approves a pending skill the agent proposed for itself via
    propose_skill (tools/universal.py) — flips it to active, at which point
    with_custom_guidance starts including it in that agent's turns."""
    store.approve_agent_custom_skill(org_id, agent_id, skill_id)
    return {"approved": True}
