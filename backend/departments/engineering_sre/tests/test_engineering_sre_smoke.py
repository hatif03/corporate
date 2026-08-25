import json
from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.engineering_sre.agents import on_task_received

_TRIAGE_LOW = json.dumps({"severity": "P3", "affected_systems": ["billing-api"], "summary": "billing API slow"})
_CASCADE_LOW = json.dumps({"cascade_risk": "low", "reasoning": "isolated to billing-api"})
_TRIAGE_HIGH = json.dumps({"severity": "P1", "affected_systems": ["auth-service"], "summary": "auth outage"})
_CASCADE_HIGH = json.dumps({"cascade_risk": "high", "reasoning": "auth outage blocks every downstream service"})
_POSTMORTEM = "Draft postmortem: incident summarized, recommend immediate investigation."


async def _fake_run_agent_turn_factory(triage_json: str, cascade_json: str):
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        stage = agent.name.rsplit("_", 1)[0]  # strips build_tiered_stage_agents' _flash/_pro suffix
        return {
            "sre_triage": triage_json,
            "sre_cascade_predictor": cascade_json,
            "sre_postmortem_drafter": _POSTMORTEM,
        }[stage]

    return fake


async def test_low_severity_incident_does_not_need_human():
    task = Task(
        id="task-1",
        title="Billing API slow",
        description="Users report billing-api p99 latency spiking.",
        task_type="handle_incident",
        status=TaskStatus.TODO,
        assignee="engineering_sre",
        created_by="ceo",
    )
    fake = await _fake_run_agent_turn_factory(_TRIAGE_LOW, _CASCADE_LOW)
    with (
        patch("departments.engineering_sre.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("app.services.store.log_activity"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", task)

    assert result.success is True
    assert result.needs_human is False
    assert result.data["severity"] == "P3"


async def test_high_severity_incident_flags_human_review():
    task = Task(
        id="task-2",
        title="Auth outage",
        description="Contact security@example.com — auth-service is fully down, call 555-000-1234.",
        task_type="handle_incident",
        status=TaskStatus.TODO,
        assignee="engineering_sre",
        created_by="ceo",
    )
    fake = await _fake_run_agent_turn_factory(_TRIAGE_HIGH, _CASCADE_HIGH)
    with (
        patch("departments.engineering_sre.agents.run_agent_turn", new=AsyncMock(side_effect=fake)) as mock_turn,
        patch("app.services.store.update_task"),
        patch("app.services.store.log_activity"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
        patch("departments.engineering_sre.agents.notify_slack_channel", new=AsyncMock(return_value={"posted": True})) as mock_notify,
    ):
        result = await on_task_received("org-test", task)

    assert result.needs_human is True
    assert result.data["severity"] == "P1"
    assert result.data["cascade_risk"] == "high"
    assert mock_notify.called
    assert mock_notify.call_args.args[0] == "org-test"

    # The PII in the task description must never reach the first (triage) call.
    first_call_prompt = mock_turn.call_args_list[0].args[4]
    assert "security@example.com" not in first_call_prompt
    assert "555-000-1234" not in first_call_prompt


async def test_low_severity_incident_does_not_notify_slack():
    task = Task(
        id="task-3",
        title="Billing API slow",
        description="Users report billing-api p99 latency spiking.",
        task_type="handle_incident",
        status=TaskStatus.TODO,
        assignee="engineering_sre",
        created_by="ceo",
    )
    fake = await _fake_run_agent_turn_factory(_TRIAGE_LOW, _CASCADE_LOW)
    with (
        patch("departments.engineering_sre.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("app.services.store.log_activity"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
        patch("departments.engineering_sre.agents.notify_slack_channel", new=AsyncMock()) as mock_notify,
    ):
        await on_task_received("org-test", task)

    assert not mock_notify.called
