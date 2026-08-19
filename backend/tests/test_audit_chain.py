from unittest.mock import MagicMock, patch

from shared import audit_chain


class _FakeDoc:
    def __init__(self, id_: str, data: dict):
        self.id = id_
        self._data = data

    def to_dict(self):
        return self._data


class _FakeAuditCollection:
    """Minimal stand-in for the Firestore collection audit_chain touches:
    org_collection(...).order_by(...).limit(...)/.stream() for reads, and
    org_doc(org_id, "audit_log", hash).set(...) for writes."""

    def __init__(self):
        self.entries: list[dict] = []

    def order_by(self, field, direction=None):
        return self

    def limit(self, n):
        reversed_entries = list(reversed(self.entries))[:n]
        return _Stream(reversed_entries)

    def stream(self):
        return _Stream(self.entries)


class _Stream:
    def __init__(self, entries):
        self._entries = entries

    def stream(self):
        return iter(_FakeDoc(e["hash"], e) for e in self._entries)

    def __iter__(self):
        return self.stream()


def _install_fake_chain():
    collection = _FakeAuditCollection()

    def fake_org_collection(org_id, name):
        assert name == "audit_log"
        return collection

    def fake_org_doc(org_id, name, doc_id):
        doc = MagicMock()

        def _set(data):
            collection.entries.append(data)

        doc.set.side_effect = _set
        return doc

    return collection, fake_org_collection, fake_org_doc


def test_append_entry_chains_to_previous_hash():
    collection, fake_org_collection, fake_org_doc = _install_fake_chain()
    with patch.object(audit_chain, "org_collection", fake_org_collection), patch.object(
        audit_chain, "org_doc", fake_org_doc
    ):
        e1 = audit_chain.append_entry("org1", "finance_audit", "task-1", "finance_audit", "on_task_received", {"x": 1})
        e2 = audit_chain.append_entry("org1", "finance_audit", "task-2", "finance_audit", "on_task_received", {"x": 2})

        assert e1.prev_hash == audit_chain.GENESIS_HASH
        assert e2.prev_hash == e1.hash

        result = audit_chain.verify_chain("org1")
        assert result.ok is True
        assert result.entry_count == 2


def test_verify_chain_detects_tampering():
    collection, fake_org_collection, fake_org_doc = _install_fake_chain()
    with patch.object(audit_chain, "org_collection", fake_org_collection), patch.object(
        audit_chain, "org_doc", fake_org_doc
    ):
        audit_chain.append_entry("org1", "finance_audit", "task-1", "finance_audit", "on_task_received", {"x": 1})
        # Tamper with the stored payload without recomputing the hash.
        collection.entries[0]["payload"]["x"] = 999

        result = audit_chain.verify_chain("org1")
        assert result.ok is False
        assert result.broken_at is not None
