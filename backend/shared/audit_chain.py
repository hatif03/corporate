"""Tamper-evident hash-chained audit log.

Every entry's hash covers the previous entry's hash, so replaying the chain
and recomputing hashes detects any single-entry tampering. Applied
automatically via the @audited_task decorator in backend/departments/base.py
— departments should not need to call append_entry directly. See ADR
docs/adr/0005-department-contract-and-scaffolding.md for how this plugs in.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.firestore_client import org_collection, org_doc

GENESIS_HASH = "0" * 64


@dataclass
class ChainEntry:
    department_id: str
    task_id: str
    actor: str
    action: str
    payload: dict[str, Any]
    prev_hash: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        material = {
            "department_id": self.department_id,
            "task_id": self.task_id,
            "actor": self.actor,
            "action": self.action,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "ts": self.ts,
        }
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "departmentId": self.department_id,
            "taskId": self.task_id,
            "actor": self.actor,
            "action": self.action,
            "payload": self.payload,
            "prevHash": self.prev_hash,
            "hash": self.hash,
            "ts": self.ts,
        }


@dataclass
class VerificationResult:
    ok: bool
    entry_count: int
    broken_at: str | None = None
    reason: str | None = None


def _last_hash(org_id: str) -> str:
    query = org_collection(org_id, "audit_log").order_by("ts", direction="DESCENDING").limit(1)
    docs = list(query.stream())
    if not docs:
        return GENESIS_HASH
    return docs[0].to_dict()["hash"]


def append_entry(
    org_id: str,
    department_id: str,
    task_id: str,
    actor: str,
    action: str,
    payload: dict[str, Any],
) -> ChainEntry:
    entry = ChainEntry(
        department_id=department_id,
        task_id=task_id,
        actor=actor,
        action=action,
        payload=payload,
        prev_hash=_last_hash(org_id),
    )
    org_doc(org_id, "audit_log", entry.hash).set(entry.as_dict())
    return entry


def verify_chain(org_id: str) -> VerificationResult:
    """Replays the whole chain in timestamp order and recomputes each hash.
    Any mismatch means the entry (or an earlier one) was tampered with."""
    docs = list(org_collection(org_id, "audit_log").order_by("ts", direction="ASCENDING").stream())
    prev_hash = GENESIS_HASH
    for i, doc in enumerate(docs):
        data = doc.to_dict()
        recomputed = ChainEntry(
            department_id=data["departmentId"],
            task_id=data["taskId"],
            actor=data["actor"],
            action=data["action"],
            payload=data["payload"],
            prev_hash=prev_hash,
            ts=data["ts"],
        )
        if recomputed.hash != data["hash"]:
            return VerificationResult(
                ok=False,
                entry_count=len(docs),
                broken_at=doc.id,
                reason=f"hash mismatch at entry {i} (doc {doc.id}): "
                f"expected {data['hash']}, recomputed {recomputed.hash}",
            )
        if data["prevHash"] != prev_hash:
            return VerificationResult(
                ok=False,
                entry_count=len(docs),
                broken_at=doc.id,
                reason=f"prev_hash mismatch at entry {i} (doc {doc.id}): "
                f"expected chain to continue from {prev_hash}, entry claims {data['prevHash']}",
            )
        prev_hash = data["hash"]
    return VerificationResult(ok=True, entry_count=len(docs))
