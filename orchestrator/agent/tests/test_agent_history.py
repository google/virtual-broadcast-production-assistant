"""Tests for the chat history loading functionality in RoutingAgent."""
# pylint: disable=protected-access
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


@pytest.mark.asyncio
async def test_before_agent_callback_loads_history_correctly(agent: RoutingAgent):
    """Verify that before_agent_callback loads and injects history correctly."""
    # Mock the context object to simulate the real structure
    mock_context = MagicMock()
    mock_context.state = {"user_id": "test_user"}

    mock_session = MagicMock()
    mock_session.events = [
        Event(author="user", content=Content(parts=[AdkPart(text="Current message")]))
    ]

    mock_invocation_context = MagicMock()
    mock_invocation_context.session = mock_session

    # This is the key part: mocking the private attribute
    mock_context._invocation_context = mock_invocation_context

    # Mock the firestore call for user preferences
    mock_doc = AsyncMock()
    mock_doc.exists = False
    agent.mock_agent_fs.client.return_value.collection.return_value.document.return_value.get = AsyncMock(
        return_value=mock_doc
    )

    # Mock the history loading function to return some past events
    past_events = [
        Event(author="user", content=Content(parts=[AdkPart(text="Past message 1")])),
        Event(author="Routing_agent", content=Content(parts=[AdkPart(text="Past response 1")])),
    ]
    agent._load_chat_history = AsyncMock(return_value=past_events)

    # Call the function under test
    await agent.before_agent_callback(mock_context)

    # --- Assertions ---
    # 1. History loading was called
    agent._load_chat_history.assert_called_once_with("test_user")

    # 2. The history_loaded flag is set
    assert mock_context.state["history_loaded"] is True

    # 3. The events list is correctly prepended
    final_events = mock_context._invocation_context.session.events
    assert len(final_events) == 3  # 2 past events + 1 current event
    assert final_events[0].content.parts[0].text == "Past message 1"
    assert final_events[1].content.parts[0].text == "Past response 1"
    assert final_events[2].content.parts[0].text == "Current message"

    # 4. Check that it doesn't run again
    await agent.before_agent_callback(mock_context)
    agent._load_chat_history.assert_called_once()  # Still called only once
