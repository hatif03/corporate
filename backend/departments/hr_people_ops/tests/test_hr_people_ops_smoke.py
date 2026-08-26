import json
from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.hr_people_ops.agents import on_task_received


async def test_policy_question_does_not_need_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "hr_intake_classifier":
            return json.dumps({"request_type": "policy_question", "summary": "asking about remote work policy"})
        return json.dumps(
            {
                "answer": "You can work remotely up to 3 days a week by default.",
                "cited_quote": "employees may work remotely up to 3 days per week by default",
            }
        )

    task = Task(
        id="task-1",
        title="Remote work question",
        description="Can I work from home 4 days a week?",
        task_type="hr_request",
        status=TaskStatus.TODO,
        assignee="hr_people_ops",
        created_by="ceo",
    )
    with (
        patch("departments.hr_people_ops.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.needs_human is False
    assert result.data["request_type"] == "policy_question"


async def test_hallucinated_citation_escalates_to_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "hr_intake_classifier":
            return json.dumps({"request_type": "policy_question", "summary": "asking about sabbaticals"})
        return json.dumps(
            {
                "answer": "Employees get an 8-week paid sabbatical after 5 years.",
                "cited_quote": "employees are entitled to an 8-week paid sabbatical after 5 years of service",
            }
        )

    task = Task(
        id="task-3",
        title="Sabbatical question",
        description="Do we offer sabbaticals?",
        task_type="hr_request",
        status=TaskStatus.TODO,
        assignee="hr_people_ops",
        created_by="ceo",
    )
    with (
        patch("departments.hr_people_ops.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is False
    assert result.needs_human is True
    assert result.data["grounded"] is False


async def test_leave_request_always_needs_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "hr_intake_classifier":
            return json.dumps({"request_type": "leave_request", "summary": "requesting 5 days PTO next month"})
        return json.dumps(
            {
                "answer": "Standard PTO accrual is 15 days/year; this needs HR approval.",
                "cited_quote": "full-time employees accrue 15 days of PTO per year",
            }
        )

    task = Task(
        id="task-2",
        title="PTO request",
        description="I'd like to take 5 days off next month, contact me at jane@example.com",
        task_type="hr_request",
        status=TaskStatus.TODO,
        assignee="hr_people_ops",
        created_by="ceo",
    )
    with (
        patch("departments.hr_people_ops.agents.run_agent_turn", new=AsyncMock(side_effect=fake)) as mock_turn,
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.needs_human is True
    assert "PTO" in result.human_question or "leave" in result.human_question.lower()

    # PII in the original request must not reach the classifier.
    first_call_prompt = mock_turn.call_args_list[0].args[4]
    assert "jane@example.com" not in first_call_prompt
