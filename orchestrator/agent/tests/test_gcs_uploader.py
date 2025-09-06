import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_httpx_client():
    """Fixture to mock the httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.content = b"test video content"
        mock_response.headers = {"content-type": "video/mp4"}
        mock_client.get = AsyncMock(return_value=mock_response)
        yield mock_client

@pytest.fixture
def mock_storage_client():
    """Fixture to mock the google.cloud.storage.Client."""
    with patch("broadcast_orchestrator.gcs_uploader.storage_client") as mock_client:
        mock_blob = MagicMock()
        mock_blob.upload_from_string = MagicMock()
        mock_blob.generate_signed_url = MagicMock(return_value="http://signed.url/test.mp4")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        yield mock_client

@pytest.fixture
def mock_firestore_client():
    """Fixture to mock the firestore_async.client."""
    with patch("broadcast_orchestrator.gcs_uploader.db") as mock_db:
        mock_doc_ref = MagicMock()
        mock_doc_ref.set = AsyncMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        yield mock_db

# --- Tests ---

async def test_cache_asset_to_gcs(
    mock_httpx_client, mock_storage_client, mock_firestore_client
):
    """Tests that cache_asset_to_gcs downloads, uploads, and updates Firestore."""
    from broadcast_orchestrator.gcs_uploader import cache_asset_to_gcs

    # Arrange
    source_url = "http://example.com/video.mp4"
    asset_id = "test-asset-123"
    bucket_name = "test-bucket"

    # Act
    await cache_asset_to_gcs(source_url, asset_id, bucket_name)

    # Assert
    mock_httpx_client.get.assert_called_once_with(source_url, follow_redirects=True)
    
    mock_storage_client.bucket.assert_called_once_with(bucket_name)
    mock_storage_client.bucket.return_value.blob.assert_called_once_with(asset_id)
    
    upload_call = mock_storage_client.bucket.return_value.blob.return_value.upload_from_string
    upload_call.assert_called_once()
    assert upload_call.call_args[0][0] == b"test video content"
    assert upload_call.call_args[1]['content_type'] == "video/mp4"

    firestore_call = mock_firestore_client.collection.return_value.document.return_value.set
    firestore_call.assert_called_once()
    firestore_data = firestore_call.call_args[0][0]
    assert firestore_data["gcs_uri"] == f"gs://{bucket_name}/{asset_id}"
    assert firestore_data["source_url"] == source_url

async def test_get_gcs_signed_url(mock_storage_client):
    """Tests the generation of a GCS signed URL."""
    from broadcast_orchestrator.gcs_uploader import get_gcs_signed_url

    # Arrange
    gcs_uri = "gs://test-bucket/test-asset-123"

    # Act
    signed_url = await get_gcs_signed_url(gcs_uri)

    # Assert
    assert signed_url == "http://signed.url/test.mp4"
    mock_storage_client.bucket.assert_called_once_with("test-bucket")
    mock_storage_client.bucket.return_value.blob.assert_called_once_with("test-asset-123")
    mock_storage_client.bucket.return_value.blob.return_value.generate_signed_url.assert_called_once()
