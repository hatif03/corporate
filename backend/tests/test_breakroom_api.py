from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_music_returns_public_url():
    with (
        patch("app.api.breakroom.generate_ambient_track", return_value=b"fake-wav-bytes"),
        patch("app.api.breakroom.upload_playable_media", return_value="https://storage.googleapis.com/bucket/orgs/demo/breakroom/x.wav") as mock_upload,
    ):
        response = client.post("/api/org/demo/breakroom/music")

    assert response.status_code == 200
    assert response.json()["url"] == "https://storage.googleapis.com/bucket/orgs/demo/breakroom/x.wav"
    assert mock_upload.call_args.args[0] == "demo"


def test_generate_music_failure_returns_502_not_a_crash():
    with (
        patch("app.api.breakroom.generate_ambient_track", side_effect=RuntimeError("quota exceeded")),
        patch("app.api.breakroom.store.log_activity") as mock_log,
    ):
        response = client.post("/api/org/demo/breakroom/music")

    assert response.status_code == 502
    assert "quota exceeded" in response.json()["detail"]
    # Regression: a prior version swallowed the exception into only the HTTP
    # response, which Cloud Run doesn't capture — a real failure in
    # production was undiagnosable after the fact for exactly this reason.
    mock_log.assert_called_once()
    assert "quota exceeded" in mock_log.call_args.args[3]
