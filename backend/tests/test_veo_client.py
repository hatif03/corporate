"""Veo promo-video generation (app/services/veo_client.py, ADR-0019) — the
kickoff and completion-check halves stay decoupled (generation is minutes,
not seconds), so each gets its own test, plus the failure path."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import veo_client


def _mock_client_for_generate(operation_name: str) -> MagicMock:
    client = MagicMock()
    client.aio.models.generate_videos = AsyncMock(return_value=MagicMock(name=operation_name))
    # MagicMock's own `name` kwarg is special (sets the mock's repr name, not
    # an attribute) — set the real attribute explicitly afterwards.
    client.aio.models.generate_videos.return_value.name = operation_name
    return client


async def test_start_video_generation_returns_operation_name():
    client = _mock_client_for_generate("projects/p/locations/l/operations/op-1")
    with patch("app.services.veo_client.genai.Client", return_value=client):
        name = await veo_client.start_video_generation("org-test", "a calm product demo")

    assert name == "projects/p/locations/l/operations/op-1"
    call_kwargs = client.aio.models.generate_videos.call_args.kwargs
    assert call_kwargs["prompt"] == "a calm product demo"
    assert "orgs/org-test/veo" in call_kwargs["config"].output_gcs_uri


async def test_check_video_generation_returns_none_while_running():
    client = MagicMock()
    client.aio.operations.get = AsyncMock(return_value=MagicMock(done=False))
    with patch("app.services.veo_client.genai.Client", return_value=client):
        result = await veo_client.check_video_generation("projects/p/locations/l/operations/op-1")

    assert result is None


async def test_check_video_generation_returns_uri_when_done():
    generated_video = MagicMock()
    generated_video.video.uri = "gs://bucket/orgs/org-test/veo/clip.mp4"
    operation = MagicMock(done=True, error=None)
    operation.result.generated_videos = [generated_video]

    client = MagicMock()
    client.aio.operations.get = AsyncMock(return_value=operation)
    with patch("app.services.veo_client.genai.Client", return_value=client):
        result = await veo_client.check_video_generation("projects/p/locations/l/operations/op-1")

    assert result == "gs://bucket/orgs/org-test/veo/clip.mp4"


async def test_check_video_generation_raises_on_operation_error():
    operation = MagicMock(done=True, error="quota exceeded")
    client = MagicMock()
    client.aio.operations.get = AsyncMock(return_value=operation)
    with patch("app.services.veo_client.genai.Client", return_value=client):
        with pytest.raises(RuntimeError, match="quota exceeded"):
            await veo_client.check_video_generation("projects/p/locations/l/operations/op-1")
