"""Org-uploadable knowledge base: joins whatever documents an org has
uploaded for a department into the same "one big string" shape the
static embedded corpora (hr_people_ops/handbook.py,
customer_support/knowledge_base.py) already are, so a department's own
grounding-prompt code doesn't change shape — only where the string comes
from. A fresh org with nothing uploaded gets the static fallback
unchanged, so this is a zero-regression addition.

ponytail: docs are joined verbatim, not embedded/searched — the static
corpora were never searched either (they're inlined into the prompt
whole), so there's nothing here for a real vector index to improve on
yet. Add semantic retrieval if a department's corpus grows large enough
that inlining everything stops being cheap.
"""

from __future__ import annotations

from app.services import store


def department_kb_text(org_id: str, department_id: str, static_fallback: str) -> str:
    docs = store.list_kb_documents(org_id, department_id)
    if not docs:
        return static_fallback
    return "\n\n".join(f"# {d.title}\n{d.text}" for d in reversed(docs))
