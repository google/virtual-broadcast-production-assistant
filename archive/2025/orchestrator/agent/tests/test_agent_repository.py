import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from broadcast_orchestrator import agent_repository

@pytest.mark.asyncio
@patch("firebase_admin.firestore_async.client")
async def test_get_all_agents_success(mock_firestore_client):
    """
    Tests that get_all_agents successfully fetches and processes agent data.
    """
    # Arrange
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    mock_agent_1 = MagicMock()
    mock_agent_1.id = "agent1"
    mock_agent_1.to_dict.return_value = {"url": "http://agent1.com", "status": "online"}

    mock_agent_2 = MagicMock()
    mock_agent_2.id = "agent2"
    mock_agent_2.to_dict.return_value = {"url": "http://agent2.com", "status": "offline"}

    # Mock the async iterator
    class AsyncIterator:
        def __init__(self, items):
            self._items = items
            self._iter = iter(self._items)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    mock_collection.stream.return_value = AsyncIterator([mock_agent_1, mock_agent_2])

    # Act
    agents = await agent_repository.get_all_agents()

    # Assert
    assert len(agents) == 2
    assert agents[0]["id"] == "agent1"
    assert agents[0]["url"] == "http://agent1.com"
    assert agents[1]["id"] == "agent2"
    assert agents[1]["status"] == "offline"
    mock_db.collection.assert_called_once_with("agent_status")


@pytest.mark.asyncio
@patch("firebase_admin.firestore_async.client")
async def test_get_all_agents_firestore_error(mock_firestore_client):
    """
    Tests that get_all_agents returns an empty list when a Firestore error occurs.
    """
    # Arrange
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_db.collection.side_effect = Exception("Firestore is down")

    # Act
    agents = await agent_repository.get_all_agents()

    # Assert
    assert agents == []
