import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_firestore_db():
    """Fixture to mock the firestore_async.client."""
    with patch("broadcast_orchestrator.timeline_tool.db") as mock_db:
        yield mock_db

async def test_get_uri_by_source_ref_id(mock_firestore_db):
    """Tests get_uri_by_source_ref_id retrieves a URI from a timeline event."""
    from broadcast_orchestrator.timeline_tool import get_uri_by_source_ref_id

    # Arrange
    asset_id = "test-asset-123"
    expected_uri = "http://example.com/video.mp4"

    mock_timeline_doc = MagicMock()
    mock_timeline_doc.to_dict.return_value = {
        "details": {
            "video_uri": expected_uri,
            "mime_type": "video/mp4"
        }
    }
    mock_query_snapshot = [mock_timeline_doc]
    
    # Mock the chained query calls
    (mock_firestore_db.collection.return_value
     .where.return_value
     .order_by.return_value
     .limit.return_value
     .get) = AsyncMock(return_value=mock_query_snapshot)

    # Act
    result_str = await get_uri_by_source_ref_id(asset_id)
    result = json.loads(result_str)

    # Assert
    assert result["uri"] == expected_uri
    assert result["mime_type"] == "video/mp4"
    mock_firestore_db.collection.assert_called_once_with("timeline_events")
