from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.workers import spawn_worker, stop_worker

router = APIRouter(prefix="/api/org/{org_id}/workers", tags=["workers"])


class SpawnWorkerRequest(BaseModel):
    source_event: str
    prompt: str
    target_agent: str | None = None
    model_tier: str = "flash"


@router.post("")
async def spawn(org_id: str, body: SpawnWorkerRequest) -> dict:
    worker_id = spawn_worker(org_id, body.source_event, body.prompt, body.target_agent, body.model_tier)
    return {"worker_id": worker_id}


@router.post("/{worker_id}/stop")
async def stop(org_id: str, worker_id: str) -> dict:
    stopped = stop_worker(org_id, worker_id)
    if not stopped:
        raise HTTPException(status_code=404, detail="worker not running")
    return {"stopped": True}
