from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import KnowledgeDoc

client = TestClient(app)


def test_list_docs_returns_store_contents():
    docs = [KnowledgeDoc(id="kb-1", title="PTO update", text="30 days now.", created_by="uid-1")]
    with patch("app.api.knowledge_base.store.list_kb_documents", return_value=docs):
        response = client.get("/api/org/demo/departments/hr_people_ops/knowledge_base")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "PTO update"


def test_create_doc_writes_through_store():
    with patch("app.api.knowledge_base.store.append_kb_document") as mock_append:
        response = client.post(
            "/api/org/demo/departments/hr_people_ops/knowledge_base",
            json={"title": "PTO update", "text": "30 days now."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "PTO update"
    assert mock_append.call_args.args[0] == "demo"
    assert mock_append.call_args.args[1] == "hr_people_ops"


def test_delete_doc_calls_store():
    with patch("app.api.knowledge_base.store.delete_kb_document") as mock_delete:
        response = client.delete("/api/org/demo/departments/hr_people_ops/knowledge_base/kb-1")

    assert response.status_code == 200
    mock_delete.assert_called_once_with("demo", "hr_people_ops", "kb-1")
