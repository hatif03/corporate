from __future__ import annotations

from fastapi import APIRouter

from shared.audit_chain import verify_chain

router = APIRouter(prefix="/api/org/{org_id}/audit", tags=["audit"])


@router.get("/verify")
async def verify(org_id: str) -> dict:
    result = verify_chain(org_id)
    return {
        "ok": result.ok,
        "entry_count": result.entry_count,
        "broken_at": result.broken_at,
        "reason": result.reason,
    }
