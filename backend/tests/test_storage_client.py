"""upload_playable_media (app/services/storage_client.py) — deliberately a
signed URL, not blob.make_public(), since the real attachments bucket has
Uniform Bucket-Level Access enabled (confirmed live), which disables
per-object ACLs entirely. This is the one regression worth guarding:
accidentally reverting to make_public() would work in local dev against a
non-UBLA test bucket but fail in production.
"""

from unittest.mock import MagicMock, patch

from app.services import storage_client


def test_upload_playable_media_signs_a_url_not_make_public():
    mock_blob = MagicMock()
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed?sig=abc"
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_credentials = MagicMock(service_account_email="corporate-backend-sa@test.iam.gserviceaccount.com", token="fake-token")

    with (
        patch.object(storage_client, "_get_bucket", return_value=mock_bucket),
        patch("app.services.storage_client.google.auth.default", return_value=(mock_credentials, "test-project")),
    ):
        url = storage_client.upload_playable_media("org-test", "breakroom", "audio/wav", b"fake-bytes")

    assert url == "https://storage.googleapis.com/signed?sig=abc"
    mock_blob.upload_from_string.assert_called_once_with(b"fake-bytes", content_type="audio/wav")
    mock_credentials.refresh.assert_called_once()
    assert mock_blob.generate_signed_url.called
    assert mock_blob.generate_signed_url.call_args.kwargs["version"] == "v4"
    # The actual regression this guards against, per the module docstring:
    # generate_signed_url() alone tries to sign with the credential's own
    # private key and fails on Cloud Run — service_account_email/access_token
    # must be passed explicitly to route through the IAM signBlob API instead.
    assert mock_blob.generate_signed_url.call_args.kwargs["service_account_email"] == "corporate-backend-sa@test.iam.gserviceaccount.com"
    assert mock_blob.generate_signed_url.call_args.kwargs["access_token"] == "fake-token"
    assert not mock_blob.make_public.called


def test_sign_existing_gcs_uri_signs_a_blob_veo_already_wrote():
    """Regression test: reproduced live — Veo's raw gs:// URI was being
    written straight into a task's videoUrl, which no browser <video> tag
    can dereference."""
    mock_blob = MagicMock()
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed?sig=xyz"
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_credentials = MagicMock(service_account_email="corporate-backend-sa@test.iam.gserviceaccount.com", token="fake-token")

    with (
        patch.object(storage_client, "_get_bucket", return_value=mock_bucket),
        patch.object(storage_client.settings, "corporate_attachments_bucket", "test-bucket"),
        patch("app.services.storage_client.google.auth.default", return_value=(mock_credentials, "test-project")),
    ):
        url = storage_client.sign_existing_gcs_uri("gs://test-bucket/orgs/demo/veo/123/sample_0.mp4")

    assert url == "https://storage.googleapis.com/signed?sig=xyz"
    mock_bucket.blob.assert_called_once_with("orgs/demo/veo/123/sample_0.mp4")


def test_sign_existing_gcs_uri_rejects_a_uri_from_a_different_bucket():
    with patch.object(storage_client.settings, "corporate_attachments_bucket", "test-bucket"):
        try:
            storage_client.sign_existing_gcs_uri("gs://some-other-bucket/file.mp4")
            assert False, "expected ValueError"
        except ValueError:
            pass
