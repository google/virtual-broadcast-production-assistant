"""
Unit tests for the agent health checker script.
"""
from unittest.mock import patch, MagicMock

import pytest
import requests

import main

@pytest.fixture
def firestore_mock():
    """Mock Firestore client and collection."""
    with patch('google.cloud.firestore.Client') as mock_client:
        mock_db = mock_client.return_value
        mock_agents_ref = mock_db.collection.return_value
        yield mock_agents_ref

@patch('requests.get')
def test_main_agent_online(mock_requests_get, firestore_mock): # pylint: disable=redefined-outer-name
    """Test when agent is online."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests_get.return_value = mock_response

    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {'url': 'http://agent1.example.com'}
    firestore_mock.stream.return_value = [mock_agent]

    main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'online',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })

@patch('requests.get', side_effect=requests.exceptions.RequestException)
def test_main_agent_offline(_mock_requests_get, firestore_mock): # pylint: disable=redefined-outer-name
    """Test when agent is offline."""
    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {'url': 'http://agent1.example.com'}
    firestore_mock.stream.return_value = [mock_agent]

    main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'offline',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })

@patch('requests.get')
def test_main_agent_error(mock_requests_get, firestore_mock): # pylint: disable=redefined-outer-name
    """Test when agent returns an error status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_requests_get.return_value = mock_response

    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {'url': 'http://agent1.example.com'}
    firestore_mock.stream.return_value = [mock_agent]

    main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'error',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })

def test_main_agent_no_url(firestore_mock): # pylint: disable=redefined-outer-name
    """Test when agent has no URL."""
    mock_agent = MagicMock()
    mock_agent.id = 'agent-1'
    mock_agent.to_dict.return_value = {}
    firestore_mock.stream.return_value = [mock_agent]

    main.main()

    firestore_mock.document('agent-1').update.assert_called_with({
        'status': 'offline',
        'last_checked': main.firestore.SERVER_TIMESTAMP
    })
