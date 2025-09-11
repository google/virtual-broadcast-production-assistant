import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from a2a.types import (
    AgentCard,
    DataPart,
    FilePart,
    FileWithUri,
    JSONRPCError,
    JSONRPCErrorResponse,
    Message,
    Part,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskStatus,
    TextPart,
)

from broadcast_orchestrator.agent import RoutingAgent


@pytest.fixture
def mock_agent_card():
    """Fixture for a mock AgentCard."""
    return AgentCard(name="Test Agent",
                     url="http://test.com",
                     description="A test agent",
                     capabilities={},
                     defaultInputModes=[],
                     defaultOutputModes=[],
                     skills=[],
                     version="1.0")


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
        mock_firestore_client, mock_get_all_agents, mock_load_instructions,
        mock_agent_card, mock_callback_context):
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
            "status": "offline",  # Should be skipped
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
        mock_firestore_client, mock_get_all_agents, mock_load_instructions,
        mock_agent_card, mock_callback_context):
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
            "id": "CUEZ_RUNDOWN_AGENT",  # Preferred
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://cuez.com/a2a"
        },
        {
            "id": "SOFIE_AGENT",  # Non-preferred rundown
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://sofie.com/a2a"
        },
        {
            "id": "some_other_agent",  # Regular agent
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
    assert mock_callback_context.state[
        "rundown_agent_config_name"] == "CUEZ_RUNDOWN_AGENT"

    # 2. Check that the non-preferred rundown agent is NOT in remote_agent_connections
    assert "SOFIE_AGENT" not in agent.remote_agent_connections

    # 3. Check that the regular agent IS in remote_agent_connections
    assert "some_other_agent" in agent.remote_agent_connections
    assert len(agent.remote_agent_connections) == 1

    # 4. Check the available_agents_list in the prompt
    assert "CUEZ_RUNDOWN_AGENT" not in mock_callback_context.state[
        "available_agents_list"]
    assert "SOFIE_AGENT" not in mock_callback_context.state[
        "available_agents_list"]
    assert "some_other_agent" in mock_callback_context.state[
        "available_agents_list"]


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
    mock_success_response.result = Message(role="agent",
                                           parts=[],
                                           message_id="dummy-id")
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
    await agent.send_message("my test agent", "do something", tool_context,
                             **{})
    mock_conn1.send_message.assert_called()

    # Match on ID with different casing
    await agent.send_message("another_agent", "do something else",
                             tool_context, **{})
    mock_conn2.send_message.assert_called()

    # Match with spaces instead of underscore in ID
    await agent.send_message("MY TEST AGENT", "do a third thing", tool_context,
                             **{})
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
    result = await agent.send_message("conflict agent", "do something",
                                      tool_context, **{})

    # Assert
    assert "Error: The agent name 'conflict agent' is ambiguous" in result[0]


@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.RemoteAgentConnections")
@patch("broadcast_orchestrator.agent.get_secret")
@patch("broadcast_orchestrator.agent.get_all_agents")
async def test_load_agents_from_firestore_with_api_key(
        mock_get_all_agents, mock_get_secret, mock_remote_agent_connections,
        mocked_agent, mock_agent_card):
    """
    Tests that _load_agents_from_firestore correctly retrieves and uses an API key.
    """
    # Arrange
    agent = mocked_agent
    mock_get_secret.return_value = "super-secret-key"
    mock_get_all_agents.return_value = [{
        "id":
        "MOMENTSLAB_AGENT",
        "status":
        "online",
        "card":
        mock_agent_card.model_dump(),
        "a2a_endpoint":
        "http://momentslab.com/a2a",
        "api_key_secret":
        "momentslab-api-key-secret"
    }]

    # Act
    await agent._load_agents_from_firestore()

    # Assert
    mock_get_secret.assert_called_once_with("momentslab-api-key-secret")
    mock_remote_agent_connections.assert_called_once()

    # Check the api_key argument in the constructor call
    args, kwargs = mock_remote_agent_connections.call_args
    assert kwargs.get("api_key") == "super-secret-key"


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
    mock_success_response.result = Message(role="agent",
                                           parts=[],
                                           message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response

    mock_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["TEST_AGENT"] = mock_conn

    task_text = "Hello, agent!"

    # Act
    await agent.send_message("Test Agent", task_text, tool_context, **{})

    # Assert
    mock_conn.send_message.assert_called_once()
    call_args = mock_conn.send_message.call_args
    sent_request: SendMessageRequest = call_args.kwargs['message_request']
    message = sent_request.params.message

    assert len(message.parts) == 1
    part = message.parts[0]
    assert isinstance(part.root, TextPart)
    assert part.root.text == "Hello, agent!"


@pytest.mark.asyncio
async def test_send_message_with_structured_data(mocked_agent):
    """
    Tests that send_message correctly handles a structured data task with kwargs
    and creates a DataPart.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    tool_context.state = {"input_message_metadata": {}}

    # Mock the agent connection
    mock_conn = MagicMock()
    mock_conn.card.name = "EVS Agent"

    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = Message(role="agent",
                                           parts=[],
                                           message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response

    mock_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["EVS_AGENT"] = mock_conn

    placeholder_uri = "https://invalid.com/vid-123/"
    real_uri = "http://real.uri/video.mp4"

    task_kwargs = {
        "input_uri": placeholder_uri,
        "prompt": "blur faces",
        "duration": 10
    }

    # Mock the resolution logic
    tool_context.state["video_assets"] = {
        "vid-123": {
            "uri": real_uri,
            "mime_type": "video/mp4"
        }
    }

    # Act
    await agent.send_message("EVS Agent", "blur_subjects", tool_context,
                             **task_kwargs)

    # Assert
    mock_conn.send_message.assert_called_once()
    call_args = mock_conn.send_message.call_args
    sent_request: SendMessageRequest = call_args.kwargs['message_request']
    message = sent_request.params.message

    assert len(message.parts) == 1
    part = message.parts[0]
    assert isinstance(part.root, DataPart)

    sent_data = part.root.data
    assert sent_data["task"] == "blur_subjects"
    assert sent_data["prompt"] == "blur faces"
    assert sent_data["duration"] == 10
    assert sent_data["input_uri"] == real_uri  # Check that the URI was resolved


@pytest.mark.asyncio
@patch("broadcast_orchestrator.agent.get_uri_by_source_ref_id",
       new_callable=AsyncMock)
async def test_uri_sanitization_and_resolution_flow(mock_get_uri,
                                                    mocked_agent):
    """
    Tests the full flow of receiving a video, sanitizing its URI for the LLM,
    and then correctly resolving the sanitized URI to a real one for a downstream agent.
    """
    # --- Part 1: Ingress and Sanitization ---

    # Arrange for receiving a response from a search agent
    agent = mocked_agent
    tool_context = MagicMock()
    tool_context.state = {"input_message_metadata": {}}

    real_video_uri = "https://real.uri/video.mp4"
    video_id = "vid-123"
    video_title = "My Awesome Video.mp4"
    video_mime = "video/mp4"

    # Mock the response from the initial search agent (e.g., Moments Lab)
    search_agent_response_part = Part(root=FilePart(file=FileWithUri(
        uri=real_video_uri, mime_type=video_mime, name="video.mp4"),
                                                    metadata={
                                                        "id": video_id,
                                                        "title": video_title
                                                    }))
    search_agent_message = Message(role="agent",
                                   parts=[search_agent_response_part],
                                   message_id="remote-msg-id")

    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = search_agent_message
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response

    mock_search_conn = MagicMock()
    mock_search_conn.card.name = "Search Agent"
    mock_search_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["SEARCH_AGENT"] = mock_search_conn

    # Act: Call send_message to process the search agent's response
    output_parts_str = await agent.send_message("Search Agent", "find video",
                                                tool_context, **{})

    # Assert: Check that the URI was sanitized for the LLM
    assert len(output_parts_str) == 1
    sanitized_part = json.loads(output_parts_str[0])

    assert sanitized_part["kind"] == "file"
    placeholder_uri = sanitized_part["file"]["uri"]
    assert placeholder_uri == f"https://invalid.com/{video_id}/"

    # Assert: Check that the real URI and mime_type were cached in the state
    assert video_id in tool_context.state["video_assets"]
    assert tool_context.state["video_assets"][video_id][
        "uri"] == real_video_uri
    assert tool_context.state["video_assets"][video_id][
        "mime_type"] == video_mime

    # --- Part 2: Egress and Resolution ---

    # Arrange for sending a task to a processing agent
    # The LLM sees the placeholder_uri and uses it in the next task
    task_for_processor = f"Blur the face in {placeholder_uri} at 15s"

    mock_processor_conn = MagicMock()
    mock_processor_conn.card.name = "Processing Agent"
    # This mock will just receive the final message, we don't need it to respond
    mock_processor_conn.send_message = AsyncMock(
        return_value=mock_send_response)
    agent.remote_agent_connections["PROCESSING_AGENT"] = mock_processor_conn

    # Act: Call send_message to send the task to the processor
    await agent.send_message("Processing Agent", task_for_processor,
                             tool_context, **{})

    # Assert: Check that the message sent to the processor contained the REAL URI
    mock_processor_conn.send_message.assert_called_once()
    call_args = mock_processor_conn.send_message.call_args
    sent_request: SendMessageRequest = call_args.kwargs['message_request']
    sent_message = sent_request.params.message

    assert len(sent_message.parts) == 2

    # Find the FilePart and TextPart
    sent_file_part = None
    sent_text_part = None
    for part in sent_message.parts:
        if isinstance(part.root, FilePart):
            sent_file_part = part.root
        if isinstance(part.root, TextPart):
            sent_text_part = part.root

    assert sent_file_part is not None
    assert sent_text_part is not None

    # Assert that the FilePart has the real URI
    assert sent_file_part.file.uri == real_video_uri
    assert sent_file_part.file.mime_type == video_mime

    # Assert that the TextPart also has the real URI
    assert real_video_uri in sent_text_part.text
    assert placeholder_uri not in sent_text_part.text


@pytest.mark.asyncio
async def test_send_message_with_filename(mocked_agent):
    """
    Tests that send_message can extract a filename from the task.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    tool_context.state = {"input_message_metadata": {}}

    # Mock the agent connection
    mock_conn = MagicMock()
    mock_conn.card.name = "EVS Agent"

    mock_success_response = MagicMock(spec=SendMessageSuccessResponse)
    mock_success_response.result = Message(role="agent",
                                           parts=[],
                                           message_id="dummy-id")
    mock_send_response = MagicMock()
    mock_send_response.root = mock_success_response

    mock_conn.send_message = AsyncMock(return_value=mock_send_response)
    agent.remote_agent_connections["EVS_AGENT"] = mock_conn

    task_text = "blur faces in measles_measles_160725_oov_1830bm_1830_16_7_105_22880234.mp4 from 15 seconds for a duration of 10 seconds"
    filename = "measles_measles_160725_oov_1830bm_1830_16_7_105_22880234.mp4"

    # Mock get_uri_by_source_ref_id to avoid firestore calls
    with patch("broadcast_orchestrator.agent.get_uri_by_source_ref_id",
               new_callable=AsyncMock) as mock_get_uri:
        mock_get_uri.return_value = json.dumps({
            "uri": "http://real.uri/video.mp4",
            "mime_type": "video/mp4"
        })

        # Act
        await agent.send_message("EVS Agent", task_text, tool_context, **{})

    # Assert
    mock_get_uri.assert_called_once_with(filename)


@pytest.mark.asyncio
async def test_send_message_retries_on_terminal_state_error(mocked_agent):
    """
    Tests that send_message clears the task_id and retries the request
    when it receives a 'task in terminal state' error.
    """
    # Arrange
    agent = mocked_agent
    tool_context = MagicMock()
    tool_context.state = {}  # Use a real dict for state testing

    agent_name = "Rundown Agent"
    canonical_id = "CUEZ_RUNDOWN_AGENT"
    task_id = "task-123-terminal"
    context_id = "context-456"

    # Set initial state with a terminal task_id
    tool_context.state[f"{canonical_id}_task_id"] = task_id
    tool_context.state[f"{canonical_id}_context_id"] = context_id
    tool_context.state["input_message_metadata"] = {}
    tool_context.state["rundown_agent_config_name"] = canonical_id

    # Mock the error response for the first call
    mock_error = JSONRPCError(
        code=-32602,
        message=f"Task {task_id} is in terminal state: TaskState.completed")
    mock_error_response = MagicMock(spec=SendMessageResponse)
    mock_error_response.root = JSONRPCErrorResponse(error=mock_error,
                                                    id="request-id",
                                                    jsonrpc="2.0")

    # Mock the success response for the second (retry) call
    mock_success_result = Task(id="new-task-456",
                               status=TaskStatus(state="working"),
                               kind="task",
                               contextId=context_id)
    mock_success_response = MagicMock(spec=SendMessageResponse)
    mock_success_response.root = SendMessageSuccessResponse(
        result=mock_success_result, id="request-id", jsonrpc="2.0")

    # Mock the agent connection
    mock_conn = MagicMock()
    mock_conn.card.name = agent_name
    # The first call gets an error, the second succeeds
    mock_conn.send_message = AsyncMock(
        side_effect=[mock_error_response, mock_success_response])

    # Set up the agent with the mocked connection
    agent.all_rundown_agents[canonical_id] = mock_conn
    tool_context.state['rundown_agent_connection'] = mock_conn

    # Act
    result = await agent.send_message(agent_name, "show me the rundown",
                                      tool_context, **{})

    # Assert
    assert mock_conn.send_message.call_count == 2

    # Assert first call had the terminal task_id
    first_call_args = mock_conn.send_message.call_args_list[0]
    first_request: SendMessageRequest = first_call_args.kwargs[
        'message_request']
    assert first_request.params.message.task_id == task_id

    # Assert second call had task_id=None
    second_call_args = mock_conn.send_message.call_args_list[1]
    second_request: SendMessageRequest = second_call_args.kwargs[
        'message_request']
    assert second_request.params.message.task_id is None

    # Assert the state was updated
    # Task ID should be cleared (set to None) and then set to the new ID
    assert tool_context.state[f"{canonical_id}_task_id"] == "new-task-456"

    # Assert the final result is from the successful retry
    assert len(result) > 0
    result_part = json.loads(result[0])
    assert result_part["id"] == "new-task-456"
