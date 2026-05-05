"""Tests for the FirestoreAgentObserver."""
# pylint: disable=redefined-outer-name, import-error, protected-access

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from broadcast_orchestrator.firestore_observer import FirestoreAgentObserver


@pytest.fixture
def observer():
    """Provides a FirestoreAgentObserver with a mocked Firestore client."""
    with patch("os.environ.get", return_value="test-project"):
        # The FirestoreAgentObserver's __init__ calls `firestore_async.client()`
        # which requires the firebase_admin app to be initialized.
        # We patch `firestore_async` within the observer's module
        # to bypass this.
        with patch("broadcast_orchestrator.firestore_observer.firestore_async"):
            observer_instance = FirestoreAgentObserver()
            mock_add = AsyncMock()
            (observer_instance.db.collection.return_value.document.return_value
             .collection.return_value.add) = mock_add
            yield observer_instance, mock_add


@pytest.fixture
def mock_context():
    """Provides a mock CallbackContext with a session_id."""
    context = MagicMock()
    context.state = {"session_id": "test-session-123"}
    return context


@pytest.fixture
def mock_tool_context():
    """Provides a mock ToolContext with a session_id."""
    context = MagicMock()
    context.state = {"session_id": "test-session-123"}
    return context


def test_before_model_logs_correct_event(observer, mock_context):
    """Verify that the before_model callback logs the correct event data."""
    observer_instance, mock_add = observer
    mock_context.model.prompt = "Prompt to the LLM"

    asyncio.run(observer_instance.before_model(context=mock_context))

    mock_add.assert_called_once()
    call_args, _ = mock_add.call_args
    event_data = call_args[0]

    assert event_data["type"] == "MODEL_START"
    assert event_data["prompt"] == "Prompt to the LLM"


def test_after_model_logs_correct_event(observer, mock_context):
    """Verify that the after_model callback logs the correct event data."""
    observer_instance, mock_add = observer
    mock_context.model.response = "Response from the LLM"

    asyncio.run(observer_instance.after_model(context=mock_context))

    mock_add.assert_called_once()
    call_args, _ = mock_add.call_args
    event_data = call_args[0]

    assert event_data["type"] == "MODEL_END"
    assert event_data["response"] == "Response from the LLM"


def test_before_tool_logs_correct_event(observer, mock_tool_context):
    """Verify that the before_tool callback logs the correct event data."""
    observer_instance, mock_add = observer
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    tool_args = {"arg1": "value1"}

    asyncio.run(observer_instance.before_tool(
        tool_context=mock_tool_context, tool=mock_tool, args=tool_args))

    mock_add.assert_called_once()
    call_args, _ = mock_add.call_args
    event_data = call_args[0]

    assert event_data["type"] == "TOOL_START"
    assert event_data["tool_name"] == "test_tool"
    assert event_data["tool_args"] == {"arg1": "value1"}


def test_after_tool_logs_correct_event(observer, mock_tool_context):
    """Verify that the after_tool callback logs the correct event data."""
    observer_instance, mock_add = observer
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    tool_response = "Tool output"

    asyncio.run(observer_instance.after_tool(
        tool_context=mock_tool_context,
        tool=mock_tool,
        tool_response=tool_response))

    mock_add.assert_called_once()
    call_args, _ = mock_add.call_args
    event_data = call_args[0]

    assert event_data["type"] == "TOOL_END"
    assert event_data["tool_name"] == "test_tool"
    assert event_data["tool_output"] == "Tool output"
