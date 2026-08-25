from unittest.mock import AsyncMock, patch

from app.models import Task, TaskStatus
from departments.marketing_comms.agents import on_task_received


def _make_task(description: str) -> Task:
    return Task(
        id="task-1",
        title="Draft launch email",
        description=description,
        task_type="marketing_request",
        status=TaskStatus.TODO,
        assignee="marketing_comms",
        created_by="ceo",
    )


async def test_clean_copy_with_cta_passes_and_gets_scheduled():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "marketing_brief_intake":
            return "B2B audience, awareness goal, short email format."
        if agent.name.rsplit("_", 1)[0] == "marketing_copy_drafter":
            return "Our new API tier cuts integration time in half. Get started today."
        return "Tuesday morning, around 9am, works well for a B2B audience."

    with (
        patch("departments.marketing_comms.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("Announce our new API tier."))

    assert result.success is True
    assert result.needs_human is False
    assert result.data["brand_voice_passed"] is True
    assert "Tuesday" in result.summary


async def test_overclaiming_copy_is_rejected_and_needs_human():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "marketing_brief_intake":
            return "General audience, awareness goal."
        if agent.name.rsplit("_", 1)[0] == "marketing_copy_drafter":
            return "We're the #1 platform in the world — guaranteed results, risk-free."
        return "should not be called"

    with (
        patch("departments.marketing_comms.agents.run_agent_turn", new=AsyncMock(side_effect=fake)) as mock_turn,
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("Write a bold launch announcement."))

    assert result.success is False
    assert result.needs_human is True
    assert result.data["brand_voice_passed"] is False
    # scheduler stage must not run for rejected copy
    called_stages = [call.args[0].name.rsplit("_", 1)[0] for call in mock_turn.call_args_list]
    assert "marketing_scheduler" not in called_stages


async def test_copy_missing_cta_is_rejected():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "marketing_brief_intake":
            return "General audience, awareness goal."
        if agent.name.rsplit("_", 1)[0] == "marketing_copy_drafter":
            return "Our new feature makes your workflow smoother than ever."
        return "should not be called"

    with (
        patch("departments.marketing_comms.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
    ):
        result = await on_task_received("org-test", _make_task("Announce the new feature."))

    assert result.success is False
    assert result.needs_human is True
    assert "no clear CTA" in result.summary
