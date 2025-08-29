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
@patch('httpx.AsyncClient')
@patch('main.get_secret', return_value='test-api-key')
@patch('main.A2AClient')
async def test_main_agent_online_with_card(mock_a2a_client, mock_get_secret,
                                           mock_http_client, firestore_mock):
    """Test an online agent that returns a card from its .well-known URL."""
    # Mock A2A response for online status
    mock_a2a_client.return_value.send_message = AsyncMock(return_value=True)

    # Mock response for .well-known/agent.json
    mock_card = {
        'url': 'http://a2a.example.com',
        'skills': [{
            'tags': ['tag1', 'tag2']
        }, {
            'tags': ['tag3', 'tag1']
        }]
    }
    mock_well_known_response = MagicMock()
    mock_well_known_response.status_code = 200
    mock_well_known_response.json.return_value = mock_card

    # Configure the mock httpx client
    async_client_instance = (
        mock_http_client.return_value.__aenter__.return_value)
    async_client_instance.get.return_value = mock_well_known_response

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

    # Verify A2AClient was called with the correct endpoint
    mock_a2a_client.assert_called_once()
    _, a2a_card_arg = mock_a2a_client.call_args[0]
    assert a2a_card_arg.url == 'http://a2a.example.com'

    firestore_mock.document('agent-1').update.assert_called_with({
        'status':
        'online',
        'last_checked':
        main.firestore.SERVER_TIMESTAMP,
        'card':
        mock_card,
        'a2a_endpoint':
        'http://a2a.example.com'
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
    firestore_mock.document('agent-1').update.assert_called_with(
        {
            'status': 'error',
            'last_checked': main.firestore.SERVER_TIMESTAMP,
            'card': None,
        }
    )


@pytest.mark.asyncio
@patch('httpx.AsyncClient')
@patch('main.A2AClient')
async def test_main_agent_offline(mock_a2a_client, mock_http_client,
                                  firestore_mock):
    """Test when agent is offline (A2A check fails)."""
    # Mock response for .well-known/agent.json
    mock_card = {'url': 'http://agent1.example.com', 'skills': []}
    mock_well_known_response = MagicMock()
    mock_well_known_response.status_code = 200
    mock_well_known_response.json.return_value = mock_card
    async_client_instance = (
        mock_http_client.return_value.__aenter__.return_value)
    async_client_instance.get.return_value = mock_well_known_response

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
        'status':
        'offline',
        'last_checked':
        main.firestore.SERVER_TIMESTAMP,
        'card':
        mock_card,
        'a2a_endpoint':
        'http://agent1.example.com'
    })


@pytest.mark.asyncio
async def test_main_agent_no_url(firestore_mock):
    """Test when agent has no URL in Firestore."""
    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {}

    async def mock_stream():
        yield mock_agent

    firestore_mock.stream.return_value = mock_stream()

    await main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status':
        'offline',
        'last_checked':
        main.firestore.SERVER_TIMESTAMP,
        'card':
        None
    })
