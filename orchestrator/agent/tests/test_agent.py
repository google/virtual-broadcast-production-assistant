import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from a2a.types import (
    AgentCard,
    FilePart,
    FileWithUri,
    Message,
    Part,
    SendMessageRequest,
    SendMessageSuccessResponse,
    TextPart,
)

from broadcast_orchestrator.agent import RoutingAgent

@pytest.fixture
def mock_agent_card():
    """Fixture for a mock AgentCard."""
    return AgentCard(
        name="Test Agent",
        url="http://test.com",
        description="A test agent",
        capabilities={},
        defaultInputModes=[],
        defaultOutputModes=[],
        skills=[],
        version="1.0"
    )

@pytest.fixture
def mock_callback_context():
    """Fixture for a mock CallbackContext."""
    context = MagicMock()
    context.state = {}
    return context

@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.load_system_instructions")
@patch("broadcast_orchestrator.agent.get_all_agents")
@patch("firebase_admin.firestore_async.client")
async def test_before_agent_callback_loads_agents_successfully(
    mock_firestore_client, mock_get_all_agents, mock_load_instructions, mock_agent_card, mock_callback_context
):
    """
    Tests that before_agent_callback successfully loads online agents
    from Firestore.
    """
    # Arrange
    agent = RoutingAgent()

    mock_get_all_agents.return_value = [
        {
            "id": "agent1",
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://agent1.com/a2a"
        },
        {
            "id": "agent2",
            "status": "offline", # Should be skipped
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://agent2.com/a2a"
        }
    ]

    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Act
    await agent.before_agent_callback(mock_callback_context)

    # Assert
    assert len(agent.remote_agent_connections) == 1
    assert "agent1" in agent.remote_agent_connections
    assert "agent2" not in agent.remote_agent_connections
    assert "agent1" in agent.cards


@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.load_system_instructions")
@patch("broadcast_orchestrator.agent.get_all_agents")
@patch("firebase_admin.firestore_async.client")
async def test_before_agent_callback_handles_rundown_agent(
    mock_firestore_client, mock_get_all_agents, mock_load_instructions, mock_agent_card, mock_callback_context
):
    """
    Tests that before_agent_callback correctly identifies and handles the
    preferred rundown agent, and filters out other rundown agents.
    """
    # Arrange
    agent = RoutingAgent()
    mock_callback_context.state = {"user_id": "test_user"}

    # Mock agents: one preferred rundown, one non-preferred rundown, and one regular agent
    mock_get_all_agents.return_value = [
        {
            "id": "CUEZ_RUNDOWN_AGENT", # Preferred
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://cuez.com/a2a"
        },
        {
            "id": "SOFIE_AGENT", # Non-preferred rundown
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://sofie.com/a2a"
        },
        {
            "id": "some_other_agent", # Regular agent
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://other.com/a2a"
        }
    ]

    # Mock user preference for 'cuez'
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"rundown_system": "cuez"}
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Act
    await agent.before_agent_callback(mock_callback_context)

    # Assert
    # 1. Check that only the preferred rundown agent is in the context
    assert "rundown_agent_connection" in mock_callback_context.state
    assert mock_callback_context.state["rundown_agent_config_name"] == "CUEZ_RUNDOWN_AGENT"

    # 2. Check that the non-preferred rundown agent is NOT in remote_agent_connections
    assert "SOFIE_AGENT" not in agent.remote_agent_connections

    # 3. Check that the regular agent IS in remote_agent_connections
    assert "some_other_agent" in agent.remote_agent_connections
    assert len(agent.remote_agent_connections) == 1

    # 4. Check the available_agents_list in the prompt
    assert "CUEZ_RUNDOWN_AGENT" not in mock_callback_context.state["available_agents_list"]
    assert "SOFIE_AGENT" not in mock_callback_context.state["available_agents_list"]
    assert "some_other_agent" in mock_callback_context.state["available_agents_list"]


@pytest.fixture
def mocked_agent():
    """Provides a RoutingAgent with its dependencies mocked."""
    with patch("broadcast_orchestrator.agent.load_system_instructions"), \
         patch("firebase_admin.firestore_async.client"), \
         patch("firebase_admin.initialize_app"):
        agent = RoutingAgent()
        yield agent


@pytest.mark.asyncio
async def test_send_message_flexible_matching(mocked_agent):
    """
    Tests that send_message can find agents with flexible, case-insensitive matching.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    # Mock the state object to allow assertions on its methods
    def state_get_side_effect(key, default=None):
        if key == "input_message_metadata":
            return default if default is not None else {}
        return None
    tool_context.state.get.side_effect = state_get_side_effect

    # Mock the agent connections
    mock_conn1 = MagicMock()
    mock_conn1.card.name = "My Test Agent"
    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = Message(role="agent", parts=[], message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response
    mock_conn1.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["MY_TEST_AGENT"] = mock_conn1

    mock_conn2 = MagicMock()
    mock_conn2.card.name = "Another Agent"
    mock_conn2.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["ANOTHER_AGENT"] = mock_conn2

    # Act & Assert
    # Case-insensitive match on card name
    await agent.send_message("my test agent", "do something", tool_context)
    mock_conn1.send_message.assert_called()

    # Match on ID with different casing
    await agent.send_message("another_agent", "do something else", tool_context)
    mock_conn2.send_message.assert_called()

    # Match with spaces instead of underscore in ID
    await agent.send_message("MY TEST AGENT", "do a third thing", tool_context)
    assert mock_conn1.send_message.call_count == 2


@pytest.mark.asyncio
async def test_send_message_ambiguous_match(mocked_agent):
    """
    Tests that send_message returns an error for ambiguous agent names.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    def state_get_side_effect(key, default=None):
        if key == "input_message_metadata":
            return default if default is not None else {}
        return None
    tool_context.state.get.side_effect = state_get_side_effect

    # Mock connections with ambiguous names
    mock_conn1 = MagicMock()
    mock_conn1.card.name = "Conflict Agent"
    agent.remote_agent_connections["CONFLICT_AGENT_1"] = mock_conn1

    mock_conn2 = MagicMock()
    mock_conn2.card.name = "Conflict Agent"
    agent.remote_agent_connections["CONFLICT_AGENT_2"] = mock_conn2

    # Act
    result = await agent.send_message("conflict agent", "do something", tool_context)

    # Assert
    assert "Error: The agent name 'conflict agent' is ambiguous" in result[0]


@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.RemoteAgentConnections")
@patch("broadcast_orchestrator.agent.get_secret")
@patch("broadcast_orchestrator.agent.get_all_agents")
async def test_load_agents_from_firestore_with_api_key(
    mock_get_all_agents, mock_get_secret, mock_remote_agent_connections, mocked_agent, mock_agent_card
):
    """
    Tests that _load_agents_from_firestore correctly retrieves and uses an API key.
    """
    # Arrange
    agent = mocked_agent
    mock_get_secret.return_value = "super-secret-key"
    mock_get_all_agents.return_value = [
        {
            "id": "MOMENTSLAB_AGENT",
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://momentslab.com/a2a",
            "api_key_secret": "momentslab-api-key-secret"
        }
    ]

    # Act
    await agent._load_agents_from_firestore()

    # Assert
    mock_get_secret.assert_called_once_with("momentslab-api-key-secret")
    mock_remote_agent_connections.assert_called_once()

    # Check the api_key argument in the constructor call
    args, kwargs = mock_remote_agent_connections.call_args
    assert kwargs.get("api_key") == "super-secret-key"


@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.get_uri_by_source_ref_id", new_callable=AsyncMock)
async def test_send_message_with_file_id(mock_get_uri, mocked_agent):
    """
    Tests that send_message correctly handles a task with a file ID,
    creating both a TextPart and a FilePart.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    # A basic state mock that allows setting values
    state = {"input_message_metadata": {}}
    tool_context.state = state

    # Mock the agent connection
    mock_conn = MagicMock()
    mock_conn.card.name = "Test Agent"
    
    # Prepare a mock successful response
    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = Message(role="agent", parts=[], message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response

    mock_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["TEST_AGENT"] = mock_conn

    # Mock the URI resolution
    mock_get_uri.return_value = '{"uri": "gs://my-bucket/my-file.mp4", "mime_type": "video/mp4"}'

    task_text = "Please add the clip with id abc-123-def-456 to the timeline."

    # Act
    await agent.send_message("Test Agent", task_text, tool_context)

    # Assert
    mock_get_uri.assert_called_once_with("abc-123-def-456")
    mock_conn.send_message.assert_called_once()

    # Inspect the call arguments for send_message
    call_args = mock_conn.send_message.call_args
    sent_request: SendMessageRequest = call_args.kwargs['message_request']

    assert isinstance(sent_request, SendMessageRequest)
    message = sent_request.params.message
    assert isinstance(message, Message)

    # Verify parts
    assert len(message.parts) == 1
    part = message.parts[0]
    assert isinstance(part.root, TextPart)
    assert "gs://my-bucket/my-file.mp4" in part.root.text
    assert "Please add the clip with" in part.root.text


@pytest.mark.asyncio
async def test_send_message_with_text_only(mocked_agent):
    """
    Tests that send_message correctly handles a simple text task.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    tool_context.state = {"input_message_metadata": {}}

    # Mock the agent connection
    mock_conn = MagicMock()
    mock_conn.card.name = "Test Agent"
    
    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = Message(role="agent", parts=[], message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response
    
    mock_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["TEST_AGENT"] = mock_conn

    task_text = "Hello, agent!"

    # Act
    await agent.send_message("Test Agent", task_text, tool_context)

    # Assert
    mock_conn.send_message.assert_called_once()
    call_args = mock_conn.send_message.call_args
    sent_request: SendMessageRequest = call_args.kwargs['message_request']
    message = sent_request.params.message

    assert len(message.parts) == 1
    part = message.parts[0]
    assert isinstance(part.root, TextPart)
    assert part.root.text == "Hello, agent!"