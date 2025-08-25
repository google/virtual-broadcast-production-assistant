"""Tests for the chat history loading functionality in RoutingAgent."""
# pylint: disable=protected-access
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from google.adk.events import Event
from google.genai.types import Content, Part as AdkPart

from broadcast_orchestrator.agent import RoutingAgent


@pytest.fixture
def agent():
    """Provides a RoutingAgent with a mocked firestore client."""
    with patch("broadcast_orchestrator.agent.firestore_async") as mock_agent_fs, patch(
        "broadcast_orchestrator.firestore_observer.firestore_async"
    ) as mock_observer_fs:
        with patch(
            "broadcast_orchestrator.agent.load_remote_agents_config",
            return_value=[],
        ):
            with patch(
                "broadcast_orchestrator.agent.load_system_instructions",
                return_value="",
            ):
                agent_instance = RoutingAgent()
                agent_instance.get_agent = MagicMock()
                agent_instance.get_agent.return_value.name = "Routing_agent"
                # Attach mocks to the instance for use in tests
                agent_instance.mock_agent_fs = mock_agent_fs
                agent_instance.mock_observer_fs = mock_observer_fs
                yield agent_instance


def test_convert_user_message_event(agent: RoutingAgent):
    """Verify that a USER_MESSAGE event is converted correctly."""
    firestore_event = {"type": "USER_MESSAGE", "prompt": "Hello, world!"}
    adk_event = agent._convert_firestore_event_to_adk_event(firestore_event)

    assert adk_event is not None
    assert adk_event.author == "user"
    assert adk_event.content.parts[0].text == "Hello, world!"


def test_convert_agent_message_event(agent: RoutingAgent):
    """Verify that an AGENT_MESSAGE event is converted correctly."""
    firestore_event = {
        "type": "AGENT_MESSAGE",
        "response": "Hello from the agent!",
    }
    adk_event = agent._convert_firestore_event_to_adk_event(firestore_event)

    assert adk_event is not None
    assert adk_event.author == "Routing_agent"
    assert adk_event.content.parts[0].text == "Hello from the agent!"


def test_convert_tool_start_event(agent: RoutingAgent):
    """Verify that a TOOL_START event is converted correctly."""
    firestore_event = {
        "type": "TOOL_START",
        "tool_name": "test_tool",
        "tool_args": {"arg1": "value1"},
    }
    adk_event = agent._convert_firestore_event_to_adk_event(firestore_event)

    assert adk_event is not None
    assert adk_event.author == "Routing_agent"
    assert adk_event.content.parts[0].function_call.name == "test_tool"
    assert adk_event.content.parts[0].function_call.args["arg1"] == "value1"


def test_convert_tool_end_event(agent: RoutingAgent):
    """Verify that a TOOL_END event is converted correctly."""
    firestore_event = {
        "type": "TOOL_END",
        "tool_name": "test_tool",
        "tool_output": "tool result",
    }
    adk_event = agent._convert_firestore_event_to_adk_event(firestore_event)

    assert adk_event is not None
    assert adk_event.author == "Routing_agent"
    assert adk_event.content.role == "user"
    assert adk_event.content.parts[0].function_response.name == "test_tool"
    assert adk_event.content.parts[0].function_response.response == {
        "output": "tool result"
    }


def test_convert_unknown_event_returns_none(agent: RoutingAgent):
    """Verify that an unknown event type returns None."""
    firestore_event = {"type": "UNKNOWN_EVENT"}
    adk_event = agent._convert_firestore_event_to_adk_event(firestore_event)
    assert adk_event is None


@pytest.mark.asyncio
async def test_load_chat_history(agent: RoutingAgent):
    """Verify that chat history is loaded and converted correctly."""
    # Mock the Firestore stream
    mock_doc1 = MagicMock()
    mock_doc1.to_dict.return_value = {"type": "USER_MESSAGE", "prompt": "Hi"}
    mock_doc2 = MagicMock()
    mock_doc2.to_dict.return_value = {
        "type": "AGENT_MESSAGE",
        "response": "Hello",
    }

    async def mock_stream():
        yield mock_doc1
        yield mock_doc2

    mock_client = agent.mock_agent_fs.client.return_value
    (
        mock_client.collection.return_value.document.return_value.collection.return_value.order_by.return_value.stream
    ).return_value = mock_stream()

    history = await agent._load_chat_history("test_user")

    assert len(history) == 2
    assert history[0].author == "user"
    assert history[0].content.parts[0].text == "Hi"
    assert history[1].author == "Routing_agent"
    assert history[1].content.parts[0].text == "Hello"


@pytest.mark.asyncio
async def test_before_agent_callback_loads_history(agent: RoutingAgent):
    """Verify that before_agent_callback loads history once."""
    # Mock the context
    mock_context = MagicMock()
    mock_context.state = {"user_id": "test_user"}
    mock_context.history = []

    # Mock the firestore call for user preferences
    mock_doc = AsyncMock()
    mock_doc.exists = False
    agent.mock_agent_fs.client.return_value.collection.return_value.document.return_value.get = AsyncMock(
        return_value=mock_doc
    )

    # Mock the history loading
    agent._load_chat_history = AsyncMock(
        return_value=[
            Event(
                author="user",
                content=Content(parts=[AdkPart(text="Old message")]),
            )
        ]
    )

    # Patch the logger to spy on it
    with patch("broadcast_orchestrator.agent.logger") as mock_logger:
        # First call should load history
        await agent.before_agent_callback(mock_context)

        agent._load_chat_history.assert_called_once_with("test_user")
        assert mock_context.state["history_loaded"] is True
        assert len(mock_context.history) == 1
        assert mock_context.history[0].content.parts[0].text == "Old message"
        mock_logger.info.assert_any_call("Injecting %d events into history", 1)

        # Second call should not load history again
        await agent.before_agent_callback(mock_context)
        agent._load_chat_history.assert_called_once()  # Still called only once
