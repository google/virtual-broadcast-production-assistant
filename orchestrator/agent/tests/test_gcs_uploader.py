import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import uuid

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_bucket_and_blob():
    """Fixture to mock the firebase_admin.storage.bucket and the blob it returns."""
    mock_blob = MagicMock()
    mock_blob.upload_from_string = MagicMock()

    mock_bucket = MagicMock()
    def configure_blob(name):
        mock_blob.name = name
        return mock_blob
    mock_bucket.blob.side_effect = configure_blob
    
    with patch("firebase_admin.storage.bucket", return_value=mock_bucket) as mock_bucket_func:
        yield mock_bucket_func, mock_bucket, mock_blob

async def test_upload_base64_image_to_gcs(mock_bucket_and_blob):
    """Tests that upload_base64_image_to_gcs correctly uploads a file and constructs a tokenized URL."""
    mock_bucket_func, mock_bucket, mock_blob = mock_bucket_and_blob
    
    from broadcast_orchestrator.gcs_uploader import upload_base64_image_to_gcs

    # Arrange
    base64_data = "aGVsbG8gd29ybGQ=" # "hello world" in base64
    filename = "test.png"
    bucket_name = "test-bucket"
    test_uuid = uuid.uuid4()

    with patch.dict(os.environ, {"GCS_BUCKET_NAME": bucket_name}), \
         patch("uuid.uuid4", return_value=test_uuid):

        # Act
        result_url = await upload_base64_image_to_gcs(base64_data, filename)

        # Assert
        mock_bucket_func.assert_called_once_with(bucket_name)
        
        expected_blob_name = f"images/{test_uuid}-{filename}"
        mock_bucket.blob.assert_called_once_with(expected_blob_name)
        
        mock_blob.upload_from_string.assert_called_once_with(
            b'hello world', content_type="image/png"
        )

        assert result_url is not None
        assert f"alt=media&token={test_uuid}" in result_url
        assert f"/o/images%2F{test_uuid}-{filename}" in result_url