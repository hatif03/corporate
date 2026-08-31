"""Veo operation polling (app/api/veo.py, ADR-0019) — the completion half
of marketing_comms' fire-and-forget Veo kickoff. Not org-scoped auth (Cloud
Scheduler hits this via require_internal_oidc, same as every other
/internal/* route) — conftest.py's _bypass_org_auth fixture already
overrides require_internal_oidc too, so these hit the router directly.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import Task, TaskStatus

client = TestClient(app)


def _task(task_id: str, result: dict | None) -> Task:
    return Task(
        id=task_id, title="t", task_type="marketing_request", status=TaskStatus.DONE,
        assignee="marketing_comms", created_by="ceo", result=result,
    )


def test_poll_leaves_still_running_operations_alone():
    with (
        patch("app.api.veo.store.list_veo_operations", return_value=[{"taskId": "task-1", "operationName": "op-1"}]),
        patch("app.api.veo.check_video_generation", new=AsyncMock(return_value=None)),
        patch("app.api.veo.store.delete_veo_operation") as mock_delete,
        patch("app.api.veo.store.update_task") as mock_update,
    ):
        response = client.post("/internal/veo/demo/poll")

    assert response.status_code == 200
    assert response.json() == {"checked": 1, "completed": 0, "failed": 0}
    assert not mock_delete.called
    assert not mock_update.called


def test_poll_writes_a_playable_signed_url_and_clears_the_generating_flag():
    """Regression test: reproduced live — the raw gs:// URI Veo hands back
    was previously written straight into task.result.videoUrl, which no
    browser <video> tag can dereference (a blank, unplayable player), and
    videoGenerating never got cleared since nothing ever set it back to
    False on completion."""
    with (
        patch("app.api.veo.store.list_veo_operations", return_value=[{"taskId": "task-1", "operationName": "op-1"}]),
        patch("app.api.veo.check_video_generation", new=AsyncMock(return_value="gs://bucket/clip.mp4")),
        patch("app.api.veo.store.get_task", return_value=_task("task-1", {"copy": "hi", "videoGenerating": True})),
        patch("app.api.veo.sign_existing_gcs_uri", return_value="https://storage.googleapis.com/signed?sig=abc") as mock_sign,
        patch("app.api.veo.store.update_task") as mock_update,
        patch("app.api.veo.store.delete_veo_operation") as mock_delete,
    ):
        response = client.post("/internal/veo/demo/poll")

    assert response.json() == {"checked": 1, "completed": 1, "failed": 0}
    mock_sign.assert_called_once_with("gs://bucket/clip.mp4")
    mock_update.assert_called_once_with(
        "demo",
        "task-1",
        result={"copy": "hi", "videoGenerating": False, "videoUrl": "https://storage.googleapis.com/signed?sig=abc"},
    )
    mock_delete.assert_called_once_with("demo", "task-1")


def test_poll_clears_operation_on_generation_failure_without_crashing():
    with (
        patch("app.api.veo.store.list_veo_operations", return_value=[{"taskId": "task-1", "operationName": "op-1"}]),
        patch("app.api.veo.check_video_generation", new=AsyncMock(side_effect=RuntimeError("content policy violation"))),
        patch("app.api.veo.store.log_activity") as mock_log,
        patch("app.api.veo.store.delete_veo_operation") as mock_delete,
    ):
        response = client.post("/internal/veo/demo/poll")

    assert response.status_code == 200
    assert response.json() == {"checked": 1, "completed": 0, "failed": 1}
    assert mock_log.called
    mock_delete.assert_called_once_with("demo", "task-1")


def test_poll_with_no_pending_operations_is_a_no_op():
    with patch("app.api.veo.store.list_veo_operations", return_value=[]):
        response = client.post("/internal/veo/demo/poll")

    assert response.json() == {"checked": 0, "completed": 0, "failed": 0}
