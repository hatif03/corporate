from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.memory_search import search_memory

router = APIRouter(prefix="/api/org/{org_id}/memory", tags=["memory"])


class MemorySearchRequest(BaseModel):
    query: str
    agent_id: str | None = None
    top_k: int = 5


@router.post("/search")
async def search(org_id: str, body: MemorySearchRequest) -> dict:
    hits = search_memory(org_id, body.query, agent_id=body.agent_id, top_k=body.top_k)
    return {
        "hits": [
            {"agentId": h.agent_id, "memoryId": h.memory_id, "text": h.text, "score": h.score} for h in hits
        ]
    }
