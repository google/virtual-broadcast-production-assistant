"""
Unit tests for the agent health checker script.
"""
# pylint: disable=unused-argument, redefined-outer-name
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import main


@pytest.fixture
def firestore_mock():
    """Mock Firestore client and collection."""
    with patch('google.cloud.firestore.AsyncClient') as mock_client:
        mock_db = mock_client.return_value
        mock_agents_ref = mock_db.collection.return_value
        mock_agents_ref.document.return_value.update = AsyncMock()
        yield mock_agents_ref


@pytest.mark.asyncio
@patch('main.get_secret', return_value='test-api-key')
@patch('main.A2AClient')
async def test_main_agent_online_with_api_key(mock_a2a_client,
                                                mock_get_secret,
                                                firestore_mock):
    """Test when an agent with an API key is online."""
    mock_a2a_client.return_value.send_message = AsyncMock(
        return_value={'status': 'ok'})

    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {
        'url': 'http://agent1.example.com',
        'api_key_secret': 'my-secret'
    }

    async def mock_stream():
        yield mock_agent

    firestore_mock.stream.return_value = mock_stream()

    await main.main()

    mock_get_secret.assert_called_once_with('my-secret')
    mock_a2a_client.assert_called_once()
    mock_a2a_client.return_value.send_message.assert_called_once()
    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'online',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })


@pytest.mark.asyncio
@patch('main.get_secret', side_effect=Exception('Secret not found'))
@patch('main.A2AClient')
async def test_main_agent_secret_failure(mock_a2a_client, mock_get_secret,
                                         firestore_mock):
    """Test when fetching the agent's API key secret fails."""
    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {
        'url': 'http://agent1.example.com',
        'api_key_secret': 'my-secret'
    }

    async def mock_stream():
        yield mock_agent

    firestore_mock.stream.return_value = mock_stream()

    await main.main()

    mock_get_secret.assert_called_once_with('my-secret')
    mock_a2a_client.assert_not_called()
    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'error',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })


@pytest.mark.asyncio
@patch('main.A2AClient')
async def test_main_agent_offline(mock_a2a_client, firestore_mock):
    """Test when agent is offline."""
    mock_a2a_client.return_value.send_message = AsyncMock(
        side_effect=Exception('Connection failed'))

    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {'url': 'http://agent1.example.com'}

    async def mock_stream():
        yield mock_agent

    firestore_mock.stream.return_value = mock_stream()

    await main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'offline',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })


@pytest.mark.asyncio
async def test_main_agent_no_url(firestore_mock):
    """Test when agent has no URL."""
    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {}

    async def mock_stream():
        yield mock_agent

    firestore_mock.stream.return_value = mock_stream()

    await main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'offline',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })
