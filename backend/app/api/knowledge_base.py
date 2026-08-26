"""Org-uploadable department knowledge base — see
app/services/knowledge_base.py's module docstring. "Upload" in v1 is plain
text (client-side FileReader.readAsText, or a pasted note); Cloud Storage
stays reserved for binary vision attachments per ADR-0013."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import KnowledgeDoc
from app.services import store
from app.services.auth import AuthenticatedUser, require_org_member

router = APIRouter(prefix="/api/org/{org_id}/departments/{department_id}/knowledge_base", tags=["knowledge_base"])


class CreateKnowledgeDocBody(BaseModel):
    title: str
    text: str


@router.get("")
async def list_docs(org_id: str, department_id: str) -> list[dict]:
    return [d.model_dump(mode="json", by_alias=True) for d in store.list_kb_documents(org_id, department_id)]


@router.post("")
async def create_doc(
    org_id: str, department_id: str, body: CreateKnowledgeDocBody, user: AuthenticatedUser = Depends(require_org_member)
) -> dict:
    doc = KnowledgeDoc(id=f"kb-{uuid.uuid4().hex[:10]}", title=body.title, text=body.text, created_by=user.uid)
    store.append_kb_document(org_id, department_id, doc)
    return doc.model_dump(mode="json", by_alias=True)


@router.delete("/{doc_id}")
async def delete_doc(org_id: str, department_id: str, doc_id: str) -> dict:
    store.delete_kb_document(org_id, department_id, doc_id)
    return {"deleted": True}
