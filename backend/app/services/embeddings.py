"""Text embeddings for semantic memory search — MVP naive-cosine approach
per docs/system_prompt.md's Phase 4 note (Vertex AI Vector Search is the
noted upgrade path for real scale, not built now)."""

from __future__ import annotations

import math
from functools import lru_cache

from google import genai

from app.config import settings

EMBEDDING_MODEL = "text-embedding-004"


@lru_cache
def _client() -> genai.Client:
    return genai.Client(
        vertexai=settings.google_genai_use_vertexai,
        project=settings.google_cloud_project,
        location=settings.vertex_location,
    )


def embed_text(text: str) -> list[float]:
    response = _client().models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return response.embeddings[0].values


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
