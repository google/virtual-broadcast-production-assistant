"""Tests for the chat history loading functionality in RoutingAgent."""
# pylint: disable=protected-access
from unittest.mock import patch, MagicMock

import pytest
from google.adk.events import Event
from google.genai.types import Content, Part as AdkPart

from broadcast_orchestrator.agent import RoutingAgent
from broadcast_orchestrator.history import \
    _convert_firestore_event_to_adk_event as convert_event


@pytest.fixture
def agent():
    """Provides a RoutingAgent with a mocked firestore client."""
    with patch("broadcast_orchestrator.agent.firestore_async"), patch(
            "broadcast_orchestrator.firestore_observer.firestore_async"):
        agent_instance = RoutingAgent()
        agent_instance.get_agent = MagicMock()
        agent_instance.get_agent.return_value.name = "Routing_agent"
        yield agent_instance


def test_convert_user_message_event(agent: RoutingAgent):
    """Verify that a USER_MESSAGE event is converted correctly."""
    firestore_event = {"type": "USER_MESSAGE", "prompt": "Hello, world!"}
    adk_event = convert_event(firestore_event, agent.get_agent().name)

    assert adk_event is not None
    assert adk_event.author == "user"
    assert adk_event.content.parts[0].text == "Hello, world!"


def test_convert_agent_message_event(agent: RoutingAgent):
    """Verify that an AGENT_MESSAGE event is converted correctly."""
    firestore_event = {
        "type": "AGENT_MESSAGE",
        "response": "Hello from the agent!",
    }
    adk_event = convert_event(firestore_event, agent.get_agent().name)

    assert adk_event is not None
    assert adk_event.author == "Routing_agent"
    assert adk_event.content.parts[0].text == "Hello from the agent!"


def test_convert_tool_start_event(agent: RoutingAgent):
    """Verify that a TOOL_START event is converted correctly."""
    firestore_event = {
        "type": "TOOL_START",
        "tool_name": "test_tool",
        "tool_args": {
            "arg1": "value1"
        },
    }
    adk_event = convert_event(firestore_event, agent.get_agent().name)

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
    adk_event = convert_event(firestore_event, agent.get_agent().name)

    assert adk_event is not None
    assert adk_event.author == "tool"
    assert adk_event.content.role == "user"
    assert adk_event.content.parts[0].function_response.name == "test_tool"
    assert adk_event.content.parts[0].function_response.response == {
        "output": "tool result"
    }


def test_convert_unknown_event_returns_none(agent: RoutingAgent):
    """Verify that an unknown event type returns None."""
    firestore_event = {"type": "UNKNOWN_EVENT"}
    adk_event = convert_event(firestore_event, agent.get_agent().name)
    assert adk_event is None
