import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import os
import uuid
import httpx # Present
import json
from typing import Dict, Any # Added

from a2a.types import AgentCard, SendMessageRequest, Part, Task, SendMessageSuccessResponse, SendMessageResponse
from orchestrator.agent.broadcast_orchestrator.agent import RoutingAgent
from orchestrator.agent.broadcast_orchestrator.remote_agent_connection import RemoteAgentConnections
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.state import State
from orchestrator.agent.broadcast_orchestrator.tests.mock_a2a_agent import MockA2AAgent # Added


# Define a default URL for mock agents if not set in environment variables
DEFAULT_MOCK_CUEZ_URL = "http://mock-cuez-agent:8001"
DEFAULT_MOCK_POSTURE_URL = "http://mock-posture-agent:10001"

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("CUEZ_AGENT_URL", DEFAULT_MOCK_CUEZ_URL)
    monkeypatch.setenv("POSTURE_STUBZY_AGENT_URL", DEFAULT_MOCK_POSTURE_URL)

@pytest.fixture
def mock_cuez_card():
    return AgentCard(
        id=str(uuid.uuid4()),
        name="MockCuezAgent",
        description="Mock Cuez Agent for testing",
        version="0.1",
        endpoints=[{"type": "A2A", "url": DEFAULT_MOCK_CUEZ_URL}],
        methods=["send_message"],
        tools=[]
    )

@pytest.fixture
def mock_posture_card():
    return AgentCard(
        id=str(uuid.uuid4()),
        name="MockPostureAgent",
        description="Mock Posture Stubzy Agent for testing",
        version="0.1",
        endpoints=[{"type": "A2A", "url": DEFAULT_MOCK_POSTURE_URL}],
        methods=["send_message"],
        tools=[]
    )

@pytest.fixture
async def mock_a2a_card_resolver_factory(mock_cuez_card, mock_posture_card):
    # This fixture will provide a factory function for creating A2ACardResolver mocks
    # It allows us to control what get_agent_card returns based on the address

    mock_resolvers = {}

    def factory(client, address): # Changed signature to match A2ACardResolver constructor
        resolver_mock = AsyncMock() # Mock for A2ACardResolver instance
        if address == DEFAULT_MOCK_CUEZ_URL:
            resolver_mock.get_agent_card = AsyncMock(return_value=mock_cuez_card)
            mock_resolvers[DEFAULT_MOCK_CUEZ_URL] = resolver_mock
        elif address == DEFAULT_MOCK_POSTURE_URL:
            resolver_mock.get_agent_card = AsyncMock(return_value=mock_posture_card)
            mock_resolvers[DEFAULT_MOCK_POSTURE_URL] = resolver_mock
        else:
            # Default behavior or raise an error if an unexpected address is used
            resolver_mock.get_agent_card = AsyncMock(side_effect=Exception(f"No mock card for {address}"))
        return resolver_mock

    # Store the created mocks for assertions later if needed, though the primary check will be on RoutingAgent
    factory.mock_resolvers = mock_resolvers
    return factory


@pytest.mark.asyncio
@patch('orchestrator.agent.broadcast_orchestrator.agent.RemoteAgentConnections') # Mock the actual RemoteAgentConnections
@patch('httpx.AsyncClient', new_callable=AsyncMock) # Mock the httpx.AsyncClient used by A2ACardResolver
async def test_routing_agent_create_initialization_and_discovery(
    MockAsyncClient, # Injected by @patch for httpx.AsyncClient
    MockRemoteAgentConnections, # Injected by @patch for RemoteAgentConnections
    mock_env_vars,
    mock_a2a_card_resolver_factory, # Our custom fixture
    mock_cuez_card,
    mock_posture_card
):
    # Patch A2ACardResolver within the agent.py module
    with patch('orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver', side_effect=mock_a2a_card_resolver_factory) as mock_resolver_constructor:

        # Expected remote agent addresses from mock_env_vars
        remote_agent_addresses = [DEFAULT_MOCK_CUEZ_URL, DEFAULT_MOCK_POSTURE_URL]

        # Ensure the httpx.AsyncClient mock is returned when RoutingAgent.create calls it
        mock_async_client_instance = MockAsyncClient.return_value

        routing_agent = await RoutingAgent.create(remote_agent_addresses)

        # 1. Verify A2ACardResolver was called for each address
        assert mock_resolver_constructor.call_count == len(remote_agent_addresses)
        # Check calls to A2ACardResolver constructor
        # The first argument to A2ACardResolver is an httpx.AsyncClient instance
        mock_resolver_constructor.assert_any_call(mock_async_client_instance, DEFAULT_MOCK_CUEZ_URL)
        mock_resolver_constructor.assert_any_call(mock_async_client_instance, DEFAULT_MOCK_POSTURE_URL)


        # 2. Verify get_agent_card was called on each resolver instance
        # Access the mocks created by the factory
        assert mock_a2a_card_resolver_factory.mock_resolvers[DEFAULT_MOCK_CUEZ_URL].get_agent_card.call_count == 1
        assert mock_a2a_card_resolver_factory.mock_resolvers[DEFAULT_MOCK_POSTURE_URL].get_agent_card.call_count == 1

        # 3. Verify RemoteAgentConnections was initialized for each discovered agent card
        assert MockRemoteAgentConnections.call_count == len(remote_agent_addresses)
        MockRemoteAgentConnections.assert_any_call(agent_card=mock_cuez_card, agent_url=DEFAULT_MOCK_CUEZ_URL)
        MockRemoteAgentConnections.assert_any_call(agent_card=mock_posture_card, agent_url=DEFAULT_MOCK_POSTURE_URL)

        # 4. Verify self.remote_agent_connections and self.cards are populated
        assert len(routing_agent.remote_agent_connections) == len(remote_agent_addresses)
        assert routing_agent.remote_agent_connections[mock_cuez_card.name] == MockRemoteAgentConnections.return_value
        assert routing_agent.remote_agent_connections[mock_posture_card.name] == MockRemoteAgentConnections.return_value

        assert len(routing_agent.cards) == len(remote_agent_addresses)
        assert routing_agent.cards[mock_cuez_card.name] == mock_cuez_card
        assert routing_agent.cards[mock_posture_card.name] == mock_posture_card

        # 5. Verify list_remote_agents
        agent_list = routing_agent.list_remote_agents()
        assert len(agent_list) == len(remote_agent_addresses)

        agent_names_and_descs_in_list = [(a['name'], a['description']) for a in agent_list]
        assert (mock_cuez_card.name, mock_cuez_card.description) in agent_names_and_descs_in_list
        assert (mock_posture_card.name, mock_posture_card.description) in agent_names_and_descs_in_list

        # 6. Verify self.agents string is populated
        assert mock_cuez_card.name in routing_agent.agents
        assert mock_cuez_card.description in routing_agent.agents
        assert mock_posture_card.name in routing_agent.agents
        assert mock_posture_card.description in routing_agent.agents


@pytest.mark.asyncio
@patch('orchestrator.agent.broadcast_orchestrator.agent.RemoteAgentConnections')
@patch('httpx.AsyncClient', new_callable=AsyncMock)
async def test_routing_agent_create_initialization_with_connect_error(
    MockAsyncClient, # Order matters, outer patch first
    MockRemoteAgentConnections,
    mock_env_vars,
    mock_posture_card # Only one agent will succeed in this test
):
    mock_async_client_instance = MockAsyncClient.return_value

    mock_resolver_constructor_patch = patch('orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver')
    mock_resolver_constructor = mock_resolver_constructor_patch.start()

    def card_resolver_side_effect(client, address): # client is the httpx.AsyncClient instance
        resolver_mock = AsyncMock()
        if address == DEFAULT_MOCK_CUEZ_URL:
            # Simulate httpx.ConnectError for CUEZ agent
            resolver_mock.get_agent_card = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        elif address == DEFAULT_MOCK_POSTURE_URL:
            resolver_mock.get_agent_card = AsyncMock(return_value=mock_posture_card)
        else:
            resolver_mock.get_agent_card = AsyncMock(side_effect=Exception(f"No mock card for {address}"))
        return resolver_mock

    mock_resolver_constructor.side_effect = card_resolver_side_effect

    remote_agent_addresses = [DEFAULT_MOCK_CUEZ_URL, DEFAULT_MOCK_POSTURE_URL]
    routing_agent = await RoutingAgent.create(remote_agent_addresses)

    # Assertions
    # A2ACardResolver constructor called for both
    assert mock_resolver_constructor.call_count == len(remote_agent_addresses)
    mock_resolver_constructor.assert_any_call(mock_async_client_instance, DEFAULT_MOCK_CUEZ_URL)
    mock_resolver_constructor.assert_any_call(mock_async_client_instance, DEFAULT_MOCK_POSTURE_URL)

    # RemoteAgentConnections should only be called for the successful one (Posture)
    MockRemoteAgentConnections.assert_called_once_with(agent_card=mock_posture_card, agent_url=DEFAULT_MOCK_POSTURE_URL)

    assert len(routing_agent.remote_agent_connections) == 1
    assert mock_posture_card.name in routing_agent.remote_agent_connections
    assert "MockCuezAgent" not in routing_agent.remote_agent_connections # Assuming default name from other fixture

    assert len(routing_agent.cards) == 1
    assert mock_posture_card.name in routing_agent.cards

    agent_list = routing_agent.list_remote_agents()
    assert len(agent_list) == 1
    assert agent_list[0]['name'] == mock_posture_card.name

    mock_resolver_constructor_patch.stop()


@pytest.mark.asyncio
@patch('httpx.AsyncClient', new_callable=AsyncMock)
async def test_routing_agent_list_remote_agents_empty(MockAsyncClient, mock_env_vars):
    # Test list_remote_agents when no agents are successfully connected
    mock_async_client_instance = MockAsyncClient.return_value
    with patch('orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver') as mock_resolver_constructor:
        # Simulate failure for all agents
        mock_resolver_instance = AsyncMock()
        mock_resolver_instance.get_agent_card = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        mock_resolver_constructor.return_value = mock_resolver_instance

        routing_agent = await RoutingAgent.create([DEFAULT_MOCK_CUEZ_URL]) # Try with one

        # Verify A2ACardResolver was called with the mocked AsyncClient
        mock_resolver_constructor.assert_called_once_with(mock_async_client_instance, DEFAULT_MOCK_CUEZ_URL)

        assert routing_agent.list_remote_agents() == []
        assert len(routing_agent.cards) == 0
        assert len(routing_agent.remote_agent_connections) == 0
        assert routing_agent.agents == "" # Should be empty string

# Minimal test for create_agent method - just checks if it returns an Agent instance
@pytest.mark.asyncio
@patch('httpx.AsyncClient', new_callable=AsyncMock)
async def test_routing_agent_create_agent_method(MockAsyncClient, mock_env_vars):
    mock_async_client_instance = MockAsyncClient.return_value
    with patch('orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver', new_callable=AsyncMock) as mock_card_resolver:
        # Setup a minimal successful discovery for one agent to allow RoutingAgent to be created fully
        mock_card_resolver_instance = mock_card_resolver.return_value
        mock_card_resolver_instance.get_agent_card = AsyncMock(return_value=AgentCard(
            id="temp-id", name="TempAgent", description="desc", version="0.1", endpoints=[{"type":"A2A", "url":DEFAULT_MOCK_CUEZ_URL}], methods=["send_message"], tools=[]
        ))

        routing_agent_instance = await RoutingAgent.create([DEFAULT_MOCK_CUEZ_URL])

        # Verify A2ACardResolver was called correctly
        mock_card_resolver.assert_called_once_with(mock_async_client_instance, DEFAULT_MOCK_CUEZ_URL)
        mock_card_resolver_instance.get_agent_card.assert_called_once()

        adk_agent = routing_agent_instance.create_agent()

        from google.adk import Agent as ADKAgent # Rename to avoid conflict
        assert isinstance(adk_agent, ADKAgent)
        assert adk_agent.name == "Routing_agent"


# Fixtures from previous step (mock_env_vars, mock_cuez_card, mock_posture_card, mock_a2a_card_resolver_factory)
# are assumed to be present in this file.

@pytest.fixture
async def initialized_routing_agent(mock_env_vars, mock_a2a_card_resolver_factory, mock_cuez_card, mock_posture_card):
    # This fixture provides a RoutingAgent that has successfully "discovered" mock agents.
    # RemoteAgentConnections class will be mocked to control its instances.

    created_rac_instances = {}

    def rac_side_effect(agent_card, agent_url):
        mock_rac_instance = AsyncMock(spec=RemoteAgentConnections)
        mock_rac_instance.agent_card = agent_card
        created_rac_instances[agent_card.name] = mock_rac_instance
        return mock_rac_instance

    # Patch httpx.AsyncClient here as well, as RoutingAgent.create uses it.
    with patch('httpx.AsyncClient', new_callable=AsyncMock) as MockAsyncClientGlobal:
      with patch('orchestrator.agent.broadcast_orchestrator.agent.RemoteAgentConnections', side_effect=rac_side_effect) as MockRACClass:
          with patch('orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver', side_effect=mock_a2a_card_resolver_factory) as MockResolverConstructor:
              agent = await RoutingAgent.create(
                  remote_agent_addresses=[DEFAULT_MOCK_CUEZ_URL, DEFAULT_MOCK_POSTURE_URL]
              )
              assert agent.remote_agent_connections[mock_cuez_card.name] is created_rac_instances[mock_cuez_card.name]
              assert agent.remote_agent_connections[mock_posture_card.name] is created_rac_instances[mock_posture_card.name]
              return agent

@pytest.fixture
def mock_tool_context():
    mock_state = State()
    mock_state["session_id"] = str(uuid.uuid4())
    tool_context = MagicMock(spec=ToolContext)
    tool_context.state = mock_state
    return tool_context

@pytest.mark.asyncio
async def test_send_message_tool_success(initialized_routing_agent, mock_tool_context, mock_cuez_card):
    agent_name_to_send_to = mock_cuez_card.name
    task_text = "Test task for Cuez agent"

    mock_rac_instance = initialized_routing_agent.remote_agent_connections[agent_name_to_send_to]

    expected_response_parts = [Part(type="text", text="Successfully processed by mock Cuez")]

    response_task = Task(
        id=str(uuid.uuid4()),
        status="completed",
        role="assistant",
        parts=expected_response_parts, # These are actual Part objects
        artifacts=[{"type": "some_artifact_type", "parts": [part.model_dump(exclude_none=True) for part in expected_response_parts]}], # Parts in artifact are dicts after json processing
        context_id=str(uuid.uuid4())
    )
    success_response_data = SendMessageSuccessResponse(
        jsonrpc="2.0",
        id=str(uuid.uuid4()),
        result=response_task
    )
    mock_send_message_response_obj = SendMessageResponse(root=success_response_data)

    mock_rac_instance.send_message = AsyncMock(return_value=mock_send_message_response_obj)

    result_parts = await initialized_routing_agent.send_message(
        agent_name=agent_name_to_send_to,
        task=task_text,
        tool_context=mock_tool_context
    )

    mock_rac_instance.send_message.assert_called_once()
    sent_message_request : SendMessageRequest = mock_rac_instance.send_message.call_args[0][0]

    assert sent_message_request.params.message.parts[0].text == task_text

    response_task.id = sent_message_request.params.message.taskId
    response_task.context_id = sent_message_request.params.message.contextId
    success_response_data.id = sent_message_request.id

    assert mock_tool_context.state["active_agent"] == agent_name_to_send_to
    assert "task_id" in mock_tool_context.state
    assert mock_tool_context.state["task_id"] == sent_message_request.params.message.taskId
    assert "context_id" in mock_tool_context.state
    assert mock_tool_context.state["context_id"] == sent_message_request.params.message.contextId

    expected_parts_as_dicts = [part.model_dump(exclude_none=True) for part in expected_response_parts]
    assert result_parts == expected_parts_as_dicts


@pytest.mark.asyncio
async def test_send_message_tool_agent_not_found(initialized_routing_agent, mock_tool_context):
    with pytest.raises(ValueError, match="Agent NonExistentAgent not found"):
        await initialized_routing_agent.send_message(
            agent_name="NonExistentAgent",
            task="Test task",
            tool_context=mock_tool_context
        )

@pytest.mark.asyncio
async def test_send_message_tool_remote_send_fails_non_success_response(initialized_routing_agent, mock_tool_context, mock_cuez_card):
    agent_name_to_send_to = mock_cuez_card.name
    task_text = "Test task for Cuez agent, expecting remote failure"

    mock_rac_instance = initialized_routing_agent.remote_agent_connections[agent_name_to_send_to]

    mock_failure_response_obj = MagicMock(spec=SendMessageResponse)
    mock_failure_response_obj.root = MagicMock()

    mock_rac_instance.send_message = AsyncMock(return_value=mock_failure_response_obj)

    result = await initialized_routing_agent.send_message(
        agent_name=agent_name_to_send_to,
        task=task_text,
        tool_context=mock_tool_context
    )
    assert result == []

@pytest.mark.asyncio
async def test_send_message_tool_remote_send_returns_non_task_result(initialized_routing_agent, mock_tool_context, mock_cuez_card):
    agent_name_to_send_to = mock_cuez_card.name
    task_text = "Test task, expecting non-Task in result"

    mock_rac_instance = initialized_routing_agent.remote_agent_connections[agent_name_to_send_to]

    success_response_data_with_bad_result = MagicMock(spec=SendMessageSuccessResponse)
    success_response_data_with_bad_result.result = MagicMock()

    mock_response_obj_bad_result = SendMessageResponse(root=success_response_data_with_bad_result)

    mock_rac_instance.send_message = AsyncMock(return_value=mock_response_obj_bad_result)

    result = await initialized_routing_agent.send_message(
        agent_name=agent_name_to_send_to,
        task=task_text,
        tool_context=mock_tool_context
    )
    assert result == []

@pytest.mark.asyncio
async def test_send_message_tool_uses_existing_task_id_and_context_id(initialized_routing_agent, mock_tool_context, mock_cuez_card):
    agent_name_to_send_to = mock_cuez_card.name
    task_text = "Test with existing IDs"

    existing_task_id = f"task_{uuid.uuid4()}"
    existing_context_id = f"context_{uuid.uuid4()}"
    mock_tool_context.state["task_id"] = existing_task_id
    mock_tool_context.state["context_id"] = existing_context_id

    mock_rac_instance = initialized_routing_agent.remote_agent_connections[agent_name_to_send_to]

    expected_response_parts = [Part(type="text", text="Response using existing IDs")]
    response_task = Task(
        id=existing_task_id, status="completed", role="assistant", parts=expected_response_parts,
        artifacts=[{"type": "some_artifact_type", "parts": [part.model_dump(exclude_none=True) for part in expected_response_parts]}],
        context_id=existing_context_id
    )
    success_response_data = SendMessageSuccessResponse(jsonrpc="2.0", id=str(uuid.uuid4()), result=response_task)
    mock_send_message_response_obj = SendMessageResponse(root=success_response_data)
    mock_rac_instance.send_message = AsyncMock(return_value=mock_send_message_response_obj)

    result_parts = await initialized_routing_agent.send_message(
        agent_name=agent_name_to_send_to,
        task=task_text,
        tool_context=mock_tool_context
    )

    sent_message_request : SendMessageRequest = mock_rac_instance.send_message.call_args[0][0]
    assert sent_message_request.params.message.taskId == existing_task_id
    assert sent_message_request.params.message.contextId == existing_context_id

    assert mock_tool_context.state["task_id"] == existing_task_id
    assert mock_tool_context.state["context_id"] == existing_context_id
    assert mock_tool_context.state["active_agent"] == agent_name_to_send_to

    expected_parts_as_dicts = [part.model_dump(exclude_none=True) for part in expected_response_parts]
    assert result_parts == expected_parts_as_dicts


@pytest.fixture
async def integration_test_routing_agent(mock_env_vars, mock_cuez_card, mock_posture_card, DEFAULT_MOCK_CUEZ_URL, DEFAULT_MOCK_POSTURE_URL):
    mock_cuez_a2a_agent_server = MockA2AAgent(
        agent_name=mock_cuez_card.name,
        agent_description=mock_cuez_card.description,
        agent_url=DEFAULT_MOCK_CUEZ_URL
    )
    # Example for a second agent if needed by tests:
    # mock_posture_a2a_agent_server = MockA2AAgent(
    #     agent_name=mock_posture_card.name,
    #     agent_description=mock_posture_card.description,
    #     agent_url=DEFAULT_MOCK_POSTURE_URL
    # )

    async def mock_get_agent_card_side_effect(client_instance, address): # client_instance is httpx.AsyncClient
        if address == DEFAULT_MOCK_CUEZ_URL:
            return mock_cuez_card
        elif address == DEFAULT_MOCK_POSTURE_URL:
             return mock_posture_card
        raise Exception(f"No mock card configured for address: {address}")

    mock_card_resolver_patch = patch(
        'orchestrator.agent.broadcast_orchestrator.agent.A2ACardResolver',
        new_callable=MagicMock # Using MagicMock to control the instance returned by the constructor
    )
    mock_card_resolver_class_mock = mock_card_resolver_patch.start()

    # This mock_resolver_instance is what the A2ACardResolver constructor will return
    mock_resolver_instance = AsyncMock(spec=True) # Use spec=True for stricter mocking
    mock_resolver_instance.get_agent_card = AsyncMock(side_effect=mock_get_agent_card_side_effect)
    mock_card_resolver_class_mock.return_value = mock_resolver_instance # Configure the class mock

    # This is the critical patch for redirecting A2AClient's HTTP calls to our mock agent
    async def mock_httpx_post(self_httpx_client, url: str, json: dict, **kwargs):
        target_mock_agent = None
        if url.startswith(DEFAULT_MOCK_CUEZ_URL):
            target_mock_agent = mock_cuez_a2a_agent_server
        # elif url.startswith(DEFAULT_MOCK_POSTURE_URL): # If using a second mock agent
        #     target_mock_agent = mock_posture_a2a_agent_server

        if target_mock_agent:
            response_data_dict = await target_mock_agent.handle_send_message(json)

            mock_http_response = MagicMock(spec=httpx.Response)
            mock_http_response.status_code = 200
            mock_http_response.json = MagicMock(return_value=response_data_dict)
            import json as original_json_dumps_module
            mock_http_response.text = original_json_dumps_module.dumps(response_data_dict)
            return mock_http_response
        else:
            mock_http_response = MagicMock(spec=httpx.Response)
            mock_http_response.status_code = 404
            import json as original_json_dumps_module
            mock_http_response.text = original_json_dumps_module.dumps({"error": f"Mock agent not found for URL {url}"})
            mock_http_response.json = MagicMock(return_value={"error": f"Mock agent not found for URL {url}"})
            mock_http_response.request = MagicMock() # Mock the request attribute
            mock_http_response.request.url = url # Set the URL on the mock request
            # Raise an HTTPStatusError for 4xx/5xx responses to mimic httpx behavior
            raise httpx.HTTPStatusError(message=f"Mock agent not found for URL {url}", request=mock_http_response.request, response=mock_http_response)


    httpx_async_client_post_patch = patch('httpx.AsyncClient.post', side_effect=mock_httpx_post, autospec=True)

    # We also need to patch httpx.AsyncClient() constructor if RoutingAgent.create() uses it directly
    # or ensure that the A2ACardResolver uses a client that has its .post mocked.
    # RoutingAgent.create makes an httpx.AsyncClient(). This client is passed to A2ACardResolver.
    # A2ACardResolver passes this client to A2AClient.
    # A2AClient uses this client to make .post calls. So patching httpx.AsyncClient.post is correct.

    mock_post = httpx_async_client_post_patch.start()

    routing_agent_instance = await RoutingAgent.create(
        remote_agent_addresses=[DEFAULT_MOCK_CUEZ_URL, DEFAULT_MOCK_POSTURE_URL]
    )

    routing_agent_instance._mock_cuez_a2a_server = mock_cuez_a2a_agent_server
    routing_agent_instance._mock_card_resolver_patch = mock_card_resolver_patch
    routing_agent_instance._httpx_async_client_post_patch = httpx_async_client_post_patch
    routing_agent_instance._mock_post_method = mock_post # Store the mock object for assertions

    yield routing_agent_instance

    mock_card_resolver_patch.stop()
    httpx_async_client_post_patch.stop()


@pytest.mark.asyncio
async def test_routing_agent_send_message_integration(integration_test_routing_agent, mock_tool_context, mock_cuez_card):
    agent_to_target = mock_cuez_card.name
    task_detail = "Integration test: Hello Cuez, please process this."

    mock_cuez_server : MockA2AAgent = integration_test_routing_agent._mock_cuez_a2a_server

    canned_response_text = "Cuez mock integration response success!"

    mock_cuez_server.default_task_response_parts = [Part(type="text", text=canned_response_text)]

    original_handle_send_message = mock_cuez_server.handle_send_message
    async def handle_send_message_with_artifacts_for_test(message_request_dict: Dict[str, Any]) -> Dict[str, Any]:
        response_dict = await original_handle_send_message(message_request_dict)

        if response_dict and response_dict.get("root") and response_dict["root"].get("result"):
            task_data = response_dict["root"]["result"]
            current_parts = task_data.get("parts", [])
            if current_parts:
                 task_data["artifacts"] = [{"type": "processed_output", "parts": current_parts}]
        return response_dict

    with patch.object(mock_cuez_server, 'handle_send_message', new=handle_send_message_with_artifacts_for_test):
        returned_parts_list_of_dicts = await integration_test_routing_agent.send_message(
            agent_name=agent_to_target,
            task=task_detail,
            tool_context=mock_tool_context
        )

    # Verification
    integration_test_routing_agent._mock_post_method.assert_called_once() # Verify httpx.AsyncClient.post was called

    assert len(mock_cuez_server.received_messages) == 1
    received_message_payload = mock_cuez_server.received_messages[0]
    assert received_message_payload['params']['message']['parts'][0]['text'] == task_detail

    generated_task_id = mock_tool_context.state["task_id"]
    generated_context_id = mock_tool_context.state["context_id"]
    assert received_message_payload['params']['message']['taskId'] == generated_task_id
    assert received_message_payload['params']['message']['contextId'] == generated_context_id

    assert mock_tool_context.state["active_agent"] == agent_to_target

    assert len(returned_parts_list_of_dicts) == 1, \
        f"Expected 1 part, got {len(returned_parts_list_of_dicts)}. Mock server received: {mock_cuez_server.received_messages}"
    assert returned_parts_list_of_dicts[0]['text'] == canned_response_text

    mock_cuez_server.clear_received_messages()
```
