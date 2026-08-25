"""Regression test for ADR-0011 gap #3: POST /tasks/{id}/answer used to
always fail with "no such question" on the very first real use, because
audited_task set has_pending_human_qa=True without ever appending a
HumanQA entry to task.human_qa. This exercises the two halves together —
what departments/base.py now writes, and what the answer endpoint reads —
rather than testing either file in isolation."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import HumanQA, Task, TaskStatus

client = TestClient(app)


def test_answering_a_department_flagged_question_actually_works():
    # Exactly what departments/base.py's _ask_human writes today (see
    # departments/tests/test_base.py) — a real HumanQA entry, not just the
    # has_pending_human_qa flag alone.
    blocked_task = Task(
        id="task-1",
        title="Qualify inbound lead",
        description="...",
        task_type="qualify_lead",
        status=TaskStatus.BLOCKED,
        assignee="sales_crm",
        created_by="ceo",
        human_qa=[HumanQA(q="Approve this discount?", asked_by="sales_crm")],
        has_pending_human_qa=True,
    )

    with (
        patch("app.api.org.store.get_task", return_value=blocked_task),
        patch("app.api.org.store.update_task") as mock_update,
        patch("app.api.org.pubsub_client.publish_message") as mock_publish,
    ):
        response = client.post("/api/org/demo/tasks/task-1/answer", json={"answer": "yes, 10% is fine"})

    assert response.status_code == 200
    assert response.json() == {"answered": True}

    updated_qa = mock_update.call_args.kwargs["human_qa"]
    assert updated_qa[0]["a"] == "yes, 10% is fine"
    assert mock_update.call_args.kwargs["has_pending_human_qa"] is False  # no more unanswered entries
    assert mock_publish.call_args.kwargs["to"] == "sales_crm"


def test_answering_when_human_qa_is_empty_fails_gracefully_not_with_index_error():
    # Belt-and-suspenders: even if some future path ever leaves human_qa
    # empty again, this must degrade to a clean error, not an unhandled
    # IndexError.
    unblocked_task = Task(
        id="task-2", title="x", description="", task_type="x",
        status=TaskStatus.BLOCKED, created_by="ceo", human_qa=[], has_pending_human_qa=True,
    )
    with patch("app.api.org.store.get_task", return_value=unblocked_task):
        response = client.post("/api/org/demo/tasks/task-2/answer", json={"answer": "..."})

    assert response.status_code == 200
    assert response.json() == {"error": "no such question"}
