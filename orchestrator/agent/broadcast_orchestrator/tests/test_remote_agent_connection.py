import pytest
import httpx
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from a2a.types import AgentCard, SendMessageRequest, MessageSendParams, Message, Part, SendMessageResponse, SendMessageSuccessResponse, Task
from orchestrator.agent.broadcast_orchestrator.remote_agent_connection import RemoteAgentConnections
from orchestrator.agent.broadcast_orchestrator.tests.mock_a2a_agent import MockA2AAgent

@pytest.fixture
def mock_a2a_server_url():
    return "http://localhost:8888/mockagent"

@pytest.fixture
def mock_agent_card(mock_a2a_server_url):
    return AgentCard(
        id=str(uuid.uuid4()),
        name="TestMockAgent",
        description="A mock agent for testing RemoteAgentConnections.",
        version="0.1",
        endpoints=[{"type": "A2A", "url": mock_a2a_server_url}],
        methods=["send_message"],
        tools=[]
    )

@pytest.fixture
async def remote_agent_connection(mock_agent_card, mock_a2a_server_url):
    # The RemoteAgentConnections class creates its own httpx.AsyncClient internally.
    # We don't need to pass one in for this test, but we need to ensure
    # its internal client will talk to our mock server or that we patch its calls.
    # For simplicity here, we'll let it try to connect, but our tests will patch the actual HTTP calls.

    # Patching A2AClient directly to avoid actual HTTP calls during RemoteAgentConnections init or usage
    with patch('orchestrator.agent.broadcast_orchestrator.remote_agent_connection.A2AClient', new_callable=AsyncMock) as MockA2AClient:
        # Configure the mock A2AClient instance that will be created inside RemoteAgentConnections
        mock_a2a_client_instance = MockA2AClient.return_value

        connection = RemoteAgentConnections(
            agent_card=mock_agent_card,
            agent_url=mock_a2a_server_url # This URL is used by A2AClient
        )
        # Store the mock client instance on the connection object for easy access in tests
        connection.mock_a2a_client_instance = mock_a2a_client_instance
        return connection

@pytest.mark.asyncio
async def test_remote_agent_connection_initialization(remote_agent_connection, mock_agent_card):
    assert remote_agent_connection.card == mock_agent_card
    assert remote_agent_connection.agent_client is not None
    # Check if A2AClient was called with the correct parameters
    # The patch context for A2AClient is within the fixture, so we access the created mock via the fixture
    assert remote_agent_connection.mock_a2a_client_instance is not None


@pytest.mark.asyncio
async def test_send_message_success(remote_agent_connection, mock_agent_card):
    mock_client = remote_agent_connection.mock_a2a_client_instance

    # Prepare a SendMessageRequest
    test_message_id = str(uuid.uuid4())
    test_task_id = str(uuid.uuid4())
    request_payload_dict = {
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Hello from test"}],
            "messageId": str(uuid.uuid4()),
            "taskId": test_task_id,
        }
    }
    message_request = SendMessageRequest(
        id=test_message_id,
        params=MessageSendParams.model_validate(request_payload_dict) # Use model_validate for Pydantic v2
    )

    # Prepare the mock response that A2AClient.send_message should return
    # This should be a SendMessageResponse object
    response_task = Task(
        id=test_task_id,
        status="completed",
        role="assistant",
        parts=[Part(type="text", text="Mock response from agent")],
        artifacts=[]
    )
    success_response_data = SendMessageSuccessResponse(
        jsonrpc="2.0",
        id=test_message_id, # Should match the request ID
        result=response_task
    )
    mock_send_message_response = SendMessageResponse(root=success_response_data)

    # Configure the mock A2AClient's send_message method
    mock_client.send_message = AsyncMock(return_value=mock_send_message_response)

    # Call the method under test
    response = await remote_agent_connection.send_message(message_request)

    # Assertions
    mock_client.send_message.assert_called_once_with(message_request)
    assert response == mock_send_message_response
    assert isinstance(response.root, SendMessageSuccessResponse)
    assert response.root.result.id == test_task_id
    assert response.root.result.parts[0].text == "Mock response from agent"

@pytest.mark.asyncio
async def test_get_agent_card(remote_agent_connection, mock_agent_card):
    assert remote_agent_connection.get_agent() == mock_agent_card
