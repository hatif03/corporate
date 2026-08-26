from unittest.mock import patch

from app.models import KnowledgeDoc
from app.services.knowledge_base import department_kb_text


def test_department_kb_text_falls_back_to_static_when_nothing_uploaded():
    with patch("app.services.knowledge_base.store.list_kb_documents", return_value=[]):
        assert department_kb_text("org-test", "hr_people_ops", static_fallback="STATIC CORPUS") == "STATIC CORPUS"


def test_department_kb_text_uses_uploaded_docs_when_present():
    docs = [
        KnowledgeDoc(id="kb-1", title="PTO policy v2", text="30 days of PTO now.", created_by="uid-1"),
    ]
    with patch("app.services.knowledge_base.store.list_kb_documents", return_value=docs):
        result = department_kb_text("org-test", "hr_people_ops", static_fallback="STATIC CORPUS")

    assert "30 days of PTO now." in result
    assert "STATIC CORPUS" not in result
