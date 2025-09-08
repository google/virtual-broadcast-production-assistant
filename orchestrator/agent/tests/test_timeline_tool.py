import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
import asyncio

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_firestore_db():
    """Fixture to mock the firestore_async.client."""
    with patch("broadcast_orchestrator.timeline_tool.db") as mock_db:
        yield mock_db

@pytest.fixture
def mock_gcs_uploader():
    """Fixture to mock the gcs_uploader module functions."""
    with patch("broadcast_orchestrator.timeline_tool.get_gcs_signed_url", new_callable=AsyncMock) as mock_get_url, \
         patch("broadcast_orchestrator.timeline_tool.cache_asset_to_gcs", new_callable=AsyncMock) as mock_cache_asset:
        yield mock_get_url, mock_cache_asset

# --- Tests ---

async def test_get_uri_by_source_ref_id_cache_hit(mock_firestore_db, mock_gcs_uploader):
    """Tests get_uri_by_source_ref_id when the asset is already in the GCS cache."""
    from broadcast_orchestrator.timeline_tool import get_uri_by_source_ref_id

    mock_get_url, _ = mock_gcs_uploader

    # Arrange
    asset_id = "test-asset-cached"
    mock_get_url.return_value = "http://gcs.signed.url/video.mp4"

    mock_cached_doc = MagicMock()
    mock_cached_doc.exists = True
    mock_cached_doc.to_dict.return_value = {
        "gcs_uri": f"gs://test-bucket/{asset_id}",
        "mime_type": "video/mp4"
    }
    mock_firestore_db.collection.return_value.document.return_value.get = AsyncMock(return_value=mock_cached_doc)

    # Act
    with patch.dict(os.environ, {"GCS_BUCKET_NAME": "test-bucket"}):
        result_str = await get_uri_by_source_ref_id(asset_id)
        result = json.loads(result_str)

    # Assert
    mock_firestore_db.collection.assert_called_once_with("media_assets")
    mock_get_url.assert_called_once_with(f"gs://test-bucket/{asset_id}")
    assert result["uri"] == "http://gcs.signed.url/video.mp4"
    assert result["mime_type"] == "video/mp4"

@patch("broadcast_orchestrator.timeline_tool.cache_asset_to_gcs", new_callable=AsyncMock)
async def test_get_uri_by_source_ref_id_cache_miss(mock_cache_asset, mock_firestore_db):
    """Tests get_uri_by_source_ref_id when the asset is not in the GCS cache."""
    from broadcast_orchestrator.timeline_tool import get_uri_by_source_ref_id

    # Arrange
    asset_id = "test-asset-not-cached"
    original_s3_url = "http://s3.com/original.mp4"

    # Mock cache miss
    mock_cached_doc = MagicMock()
    mock_cached_doc.exists = False
    mock_media_assets_collection = MagicMock()
    mock_media_assets_collection.document.return_value.get = AsyncMock(return_value=mock_cached_doc)

    # Mock timeline event lookup
    mock_timeline_doc = MagicMock()
    mock_timeline_doc.to_dict.return_value = {
        "details": {
            "video_uri": original_s3_url,
            "mime_type": "video/quicktime"
        }
    }
    mock_timeline_query_snapshot = [mock_timeline_doc]
    mock_timeline_collection = MagicMock()
    mock_timeline_collection.where.return_value.order_by.return_value.limit.return_value.get = AsyncMock(return_value=mock_timeline_query_snapshot)

    # Set up the main db mock to return the correct collection mock based on the name
    def collection_side_effect(name):
        if name == "media_assets":
            return mock_media_assets_collection
        elif name == "timeline_events":
            return mock_timeline_collection
        return MagicMock()
    mock_firestore_db.collection.side_effect = collection_side_effect

    # Act
    with patch.dict(os.environ, {"GCS_BUCKET_NAME": "test-bucket"}):
        result_str = await get_uri_by_source_ref_id(asset_id)
        result = json.loads(result_str)
    
    # Yield control to the event loop to allow the background task to run
    await asyncio.sleep(0)

    # Assert
    assert mock_firestore_db.collection.call_count == 2
    assert result["uri"] == original_s3_url
    assert result["mime_type"] == "video/quicktime"

    # Check that the background task was triggered correctly
    mock_cache_asset.assert_called_once_with(
        source_url=original_s3_url,
        asset_id=asset_id,
        gcs_bucket_name="test-bucket"
    )


async def test_get_uri_by_title_prefix_match(mock_firestore_db):
    """Tests that get_uri_by_title can find an event with a prefix match."""
    from broadcast_orchestrator.timeline_tool import get_uri_by_title

    # Arrange
    title_prefix = "My Video"
    full_title = "My Video_blur"
    session_id = "test-session"
    expected_details = {"video_uri": "http://server.com/blurred.mp4", "title": full_title}

    # Mock timeline event lookup
    mock_timeline_doc = MagicMock()
    mock_timeline_doc.to_dict.return_value = {"details": expected_details}
    mock_timeline_query_snapshot = [mock_timeline_doc]
    
    # Mock the chained calls for the query
    mock_where1 = MagicMock()
    mock_where2 = MagicMock()
    mock_where3 = MagicMock()
    mock_order1 = MagicMock()
    mock_order2 = MagicMock()
    mock_limit = MagicMock()
    
    mock_firestore_db.collection.return_value.where.return_value = mock_where1
    mock_where1.where.return_value = mock_where2
    mock_where2.where.return_value = mock_where3
    mock_where3.order_by.return_value = mock_order1
    mock_order1.order_by.return_value = mock_order2
    mock_order2.limit.return_value = mock_limit
    mock_limit.get = AsyncMock(return_value=mock_timeline_query_snapshot)

    # Act
    result_str = await get_uri_by_title(title_prefix, session_id)
    result = json.loads(result_str)

    # Assert
    # Check that the query was constructed correctly for a prefix search
    mock_firestore_db.collection.assert_called_once_with("timeline_events")
    mock_firestore_db.collection.return_value.where.assert_called_with("session_id", "==", session_id)
    mock_where1.where.assert_called_with("title", ">=", title_prefix)
    
    assert result == expected_details