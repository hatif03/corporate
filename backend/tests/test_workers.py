import asyncio
from unittest.mock import AsyncMock, patch

from app.models import WorkerStatus
from app.services import workers


async def test_spawn_worker_runs_to_completion_and_records_result():
    with (
        patch("app.services.workers.store.create_worker") as mock_create,
        patch("app.services.workers.store.update_worker") as mock_update,
        patch("app.services.workers.run_agent_turn", new=AsyncMock(return_value="handled it")),
    ):
        worker_id = workers.spawn_worker("org-test", "slack-dm", "someone asked a question in #general")
        assert mock_create.called

        # spawn_worker fires an asyncio task; give it a turn to run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    statuses = [call.args[2] for call in mock_update.call_args_list]
    assert WorkerStatus.RUNNING in statuses
    assert WorkerStatus.DONE in statuses
    assert worker_id.startswith("worker-")


async def test_spawn_worker_folds_target_agent_hint_into_prompt_and_picks_tier():
    with (
        patch("app.services.workers.store.create_worker"),
        patch("app.services.workers.store.update_worker"),
        patch("app.services.workers.run_agent_turn", new=AsyncMock(return_value="handled it")) as mock_run,
    ):
        workers.spawn_worker("org-test", "slack-dm", "billing looks off", target_agent="finance_audit", model_tier="pro")
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    agent_arg, _session, _org, _worker_id, prompt_arg = mock_run.call_args.args
    assert agent_arg is workers._worker_agents["pro"]
    assert prompt_arg.startswith("(Likely belongs to: finance_audit)")
    assert "billing looks off" in prompt_arg


async def test_spawn_worker_records_failure_on_exception():
    with (
        patch("app.services.workers.store.create_worker"),
        patch("app.services.workers.store.update_worker") as mock_update,
        patch("app.services.workers.run_agent_turn", new=AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        workers.spawn_worker("org-test", "slack-dm", "this will fail")
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    statuses = [call.args[2] for call in mock_update.call_args_list]
    assert WorkerStatus.FAILED in statuses


async def test_spawn_worker_and_await_returns_result_directly():
    with (
        patch("app.services.workers.store.create_worker"),
        patch("app.services.workers.store.update_worker"),
        patch("app.services.workers.run_agent_turn", new=AsyncMock(return_value="sub-agent's real answer")),
    ):
        result = await workers.spawn_worker_and_await("org-test", "subagent-of-ceo", "research X")

    assert result["reply"] == "sub-agent's real answer"
    assert result["worker_id"].startswith("worker-")


async def test_spawn_worker_and_await_times_out():
    async def _never_finishes(*args, **kwargs):
        await asyncio.sleep(10)
        return "should not get here"

    with (
        patch("app.services.workers.store.create_worker"),
        patch("app.services.workers.store.update_worker") as mock_update,
        patch("app.services.workers.run_agent_turn", new=AsyncMock(side_effect=_never_finishes)),
        patch("app.services.workers.SUBAGENT_TIMEOUT_SECONDS", 0.01),
    ):
        result = await workers.spawn_worker_and_await("org-test", "subagent-of-ceo", "slow research")

    assert "timed out" in result["error"]
    assert any(call.args[2] == WorkerStatus.FAILED for call in mock_update.call_args_list)


async def test_stop_worker_cancels_running_task():
    async def _never_finishes(*args, **kwargs):
        await asyncio.sleep(10)
        return "should not get here"

    with (
        patch("app.services.workers.store.create_worker"),
        patch("app.services.workers.store.update_worker") as mock_update,
        patch("app.services.workers.run_agent_turn", new=AsyncMock(side_effect=_never_finishes)),
    ):
        worker_id = workers.spawn_worker("org-test", "slack-dm", "slow one")
        await asyncio.sleep(0)  # let it start running

        stopped = workers.stop_worker("org-test", worker_id)
        assert stopped is True
        assert any(call.args[2] == WorkerStatus.FAILED for call in mock_update.call_args_list)

        # stopping an already-finished/unknown worker returns False
        assert workers.stop_worker("org-test", "worker-does-not-exist") is False
