import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.agent.broadcast_orchestrator.timeline_manager import (
    _parse_spelling_errors_from_text,
    process_tool_output_for_timeline,
)

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_generative_model():
    """Fixture to mock the Gemini GenerativeModel."""
    with patch("google.generativeai.GenerativeModel") as mock_model_class:
        mock_model_instance = mock_model_class.return_value
        mock_model_instance.generate_content_async = AsyncMock()
        yield mock_model_instance


class MockGeminiResponse:
    def __init__(self, text):
        self.text = text

# --- Tests for _parse_spelling_errors_from_text ---

async def test_parse_spelling_errors_success(mock_generative_model):
    """
    Tests successful parsing of spelling errors from text using a mocked Gemini response.
    """
    sample_text = '... "Olypics" is misspelled, it should be "Olympics". ...'
    mock_response_json = json.dumps([
        {
            "original": "Olypics",
            "suggestion": "Olympics",
            "context": "Winter Olypics to be held in French Alps in 2031",
        }
    ])
    mock_generative_model.generate_content_async.return_value = MockGeminiResponse(
        f"```json\n{mock_response_json}\n```"
    )

    result = await _parse_spelling_errors_from_text(sample_text)

    assert len(result) == 1
    assert result[0]["original"] == "Olypics"
    assert result[0]["suggestion"] == "Olympics"
    mock_generative_model.generate_content_async.assert_called_once()


async def test_parse_spelling_errors_no_errors_found(mock_generative_model):
    """
    Tests the case where the text contains no spelling errors.
    """
    sample_text = "This text is all correct."
    mock_generative_model.generate_content_async.return_value = MockGeminiResponse("[]")

    result = await _parse_spelling_errors_from_text(sample_text)

    assert result == []


async def test_parse_spelling_errors_invalid_json(mock_generative_model):
    """
    Tests the case where Gemini returns a non-JSON string.
    """
    sample_text = "Some text with errors."
    mock_generative_model.generate_content_async.return_value = MockGeminiResponse(
        "This is not JSON."
    )

    result = await _parse_spelling_errors_from_text(sample_text)

    assert result == []


# --- Tests for process_tool_output_for_timeline ---

@pytest.fixture
def mock_tool_context():
    """Fixture to create a mock ToolContext."""
    tool_context = MagicMock()
    tool_context.state = {
        "user_id": "test_user",
        "session_id": "test_session",
        "last_a2a_response": None, # This will be set in each test
    }
    return tool_context


@pytest.fixture
def mock_firestore_client():
    """Fixture to mock the Firestore client and its methods."""
    with patch("firebase_admin.firestore_async.client") as mock_client_class:
        mock_db = mock_client_class.return_value
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set = AsyncMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        # Make the mock usable in `async with`
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        yield mock_db


@patch("orchestrator.agent.broadcast_orchestrator.timeline_manager._parse_spelling_errors_from_text", new_callable=AsyncMock)
async def test_process_tool_output_creates_spelling_event(
    mock_parser, mock_firestore_client, mock_tool_context
):
    """
    Tests that process_tool_output_for_timeline correctly creates a SPELLING_ERROR event.
    """
    # 1. Setup Mocks
    mock_parser.return_value = [
        {
            "original": "Olypics",
            "suggestion": "Olympics",
            "context": "Winter Olypics 2031",
        }
    ]

    posture_agent_response = {
        "parts": [{"text": "Your text contained a word that is misspelled."}]
    }
    mock_tool_context.state["last_a2a_response"] = json.dumps(posture_agent_response)

    mock_tool = MagicMock()
    mock_tool.name = "send_message"

    # 2. Call the function
    await process_tool_output_for_timeline(tool=mock_tool, tool_context=mock_tool_context)

    # 3. Assertions
    mock_parser.assert_called_once_with("Your text contained a word that is misspelled.")

    mock_firestore_client.collection.assert_called_with("timeline_events")

    # Check that doc.set was called
    set_call = mock_firestore_client.collection.return_value.document.return_value.set
    set_call.assert_called_once()

    # Check the data that was passed to doc.set
    event_data = set_call.call_args[0][0]
    assert event_data["type"] == "SPELLING_ERROR"
    assert event_data["category"] == "CHECKS"
    assert event_data["title"] == "Spelling Suggestion"
    assert event_data["status"] == "pending"
    assert event_data["details"]["original_word"] == "Olypics"
    assert event_data["details"]["suggested_correction"] == "Olympics"
    assert "id" in event_data
    assert "user_id" in event_data
    assert "session_id" in event_data
    assert "timestamp" in event_data


async def test_process_tool_output_handles_no_events(mock_firestore_client, mock_tool_context):
    """
    Tests that no Firestore events are written when the response contains no actionable items.
    """
    # 1. Setup Mocks
    no_action_response = {
        "parts": [{"text": "Everything looks correct."}]
    }
    mock_tool_context.state["last_a2a_response"] = json.dumps(no_action_response)

    mock_tool = MagicMock()
    mock_tool.name = "send_message"

    # 2. Call the function
    await process_tool_output_for_timeline(tool=mock_tool, tool_context=mock_tool_context)

    # 3. Assertions
    set_call = mock_firestore_client.collection.return_value.document.return_value.set
    set_call.assert_not_called()
