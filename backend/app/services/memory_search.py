"""Semantic memory search: 'what does the hive know about X'. Naive-cosine
over stored embeddings — see app/services/embeddings.py's module docstring
for the Vertex AI Vector Search upgrade path once this needs to scale
beyond a handful of agents' worth of memory.

ponytail: searching "across the whole hive" (agent_id=None) fetches every
agent's memory subcollection individually rather than a single Firestore
collection-group query, since a collection-group query on `memory` would
span every org, not just this one, without a redundant orgId field on each
doc. Fine at demo scale (a handful of agents); revisit if this becomes a
real bottleneck.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services import store
from app.services.embeddings import cosine_similarity, embed_text


@dataclass
class MemoryHit:
    agent_id: str
    memory_id: str
    text: str
    score: float


def search_memory(org_id: str, query: str, agent_id: str | None = None, top_k: int = 5) -> list[MemoryHit]:
    query_embedding = embed_text(query)
    agent_ids = [agent_id] if agent_id else [a.id for a in store.list_agents(org_id)]

    hits: list[MemoryHit] = []
    for aid in agent_ids:
        for entry in store.list_memory(org_id, aid, limit_count=200):
            embedding = entry.get("embedding")
            if not embedding:
                continue
            score = cosine_similarity(query_embedding, embedding)
            hits.append(MemoryHit(agent_id=aid, memory_id=entry["id"], text=entry["text"], score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
