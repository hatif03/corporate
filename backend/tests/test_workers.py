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
