from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Task, TaskStatus
from departments.marketing_comms.agents import on_task_received


def _verifier_answers(text: str):
    """The independent_review aspect checker (shared/cross_model_check.py,
    ADR-0019) makes a real Vertex AI call unless patched."""
    return patch(
        "shared.cross_model_check.genai.Client",
        return_value=MagicMock(aio=MagicMock(models=MagicMock(generate_content=AsyncMock(return_value=MagicMock(text=text))))),
    )


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
        _verifier_answers("yes"),
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
        # Overclaiming copy should plausibly read as suspicious to an
        # independent reviewer too, not just this department's own
        # deterministic checkers.
        _verifier_answers("no"),
    ):
        result = await on_task_received("org-test", _make_task("Write a bold launch announcement."))

    assert result.success is False
    assert result.needs_human is True
    assert result.data["brand_voice_passed"] is False
    # scheduler stage must not run for rejected copy
    called_stages = [call.args[0].name.rsplit("_", 1)[0] for call in mock_turn.call_args_list]
    assert "marketing_scheduler" not in called_stages


async def test_video_request_kicks_off_veo_without_blocking_task_completion():
    """A 'video' keyword in the task description (ADR-0019) kicks off Veo
    generation as a fire-and-forget side effect — the task still completes
    (DONE) immediately with the copy; the video arrives later via
    app/api/veo.py's polling endpoint, not by this call blocking on it."""

    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "marketing_brief_intake":
            return "B2B audience, awareness goal, short email format."
        if agent.name.rsplit("_", 1)[0] == "marketing_copy_drafter":
            return "Our new API tier cuts integration time in half. Get started today."
        return "Tuesday morning works well."

    with (
        patch("departments.marketing_comms.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
        patch(
            "departments.marketing_comms.agents.start_video_generation",
            new=AsyncMock(return_value="projects/p/locations/l/operations/op-1"),
        ) as mock_start,
        patch("departments.marketing_comms.agents.store.create_veo_operation") as mock_create_op,
        _verifier_answers("yes"),
    ):
        result = await on_task_received(
            "org-test", _make_task("Announce our new API tier. Also generate a short promo video.")
        )

    assert result.success is True
    assert result.needs_human is False
    assert result.data["videoGenerating"] is True
    assert "generating in the background" in result.summary
    mock_start.assert_called_once()
    mock_create_op.assert_called_once_with("org-test", "task-1", "projects/p/locations/l/operations/op-1")


async def test_no_video_keyword_skips_veo_entirely():
    async def fake(agent, session_service, org_id, agent_id, prompt, attachment=None):
        if agent.name.rsplit("_", 1)[0] == "marketing_brief_intake":
            return "B2B audience, awareness goal, short email format."
        if agent.name.rsplit("_", 1)[0] == "marketing_copy_drafter":
            return "Our new API tier cuts integration time in half. Get started today."
        return "Tuesday morning works well."

    with (
        patch("departments.marketing_comms.agents.run_agent_turn", new=AsyncMock(side_effect=fake)),
        patch("app.services.store.update_task"),
        patch("shared.audit_chain.append_entry"),
        patch("app.services.pubsub_client.publish_message"),
        patch("departments.marketing_comms.agents.start_video_generation") as mock_start,
        _verifier_answers("yes"),
    ):
        result = await on_task_received("org-test", _make_task("Announce our new API tier."))

    assert "videoGenerating" not in result.data
    assert not mock_start.called


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
        # Required, not just thematic: with 3 aspects now, an independent
        # "yes" here would push the vote to exactly the 2/3 pass threshold
        # and flip this test's expected failure to a pass.
        _verifier_answers("no"),
    ):
        result = await on_task_received("org-test", _make_task("Announce the new feature."))

    assert result.success is False
    assert result.needs_human is True
    assert "no clear CTA" in result.summary
