import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from broadcast_orchestrator.timeline_manager import (
    _extract_parts_from_response,
    _parse_spelling_errors_from_text,
    _process_spelling_errors,
    _process_video_clips,
    _save_timeline_events,
    process_tool_output_for_timeline,
)

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


# --- Mocks and Fixtures ---


@pytest.fixture
def mock_gemini_client():
    """Fixture to mock the Gemini Client."""
    with patch(
        "broadcast_orchestrator.timeline_manager.gemini_client"
    ) as mock_client:
        # Navigate through the mock's structure to set the async method
        mock_client.aio.models.generate_content = AsyncMock()
        yield mock_client


class MockGeminiResponse:
    """A mock response object for Gemini client calls."""

    def __init__(self, text):
        self.text = text


@pytest.fixture
def mock_tool_context():
    """Fixture to create a mock ToolContext."""
    tool_context = MagicMock()
    tool_context.state = {
        "user_id": "test_user",
        "session_id": "test_session",
        "last_a2a_response": None,  # This will be set in each test
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
        yield mock_db


# --- Unit Tests for Helper Functions ---


async def test_parse_spelling_errors_success(mock_gemini_client):
    """Tests successful parsing of spelling errors from text."""
    sample_text = '... "Olypics" is misspelled, it should be "Olympics". ...'
    mock_response_json = json.dumps(
        [{
            "original": "Olypics",
            "suggestion": "Olympics",
            "context": "Winter Olypics 2031",
        }]
    )
    mock_gemini_client.aio.models.generate_content.return_value = MockGeminiResponse(
        f"```json\n{mock_response_json}\n```"
    )

    result = await _parse_spelling_errors_from_text(sample_text)

    assert len(result) == 1
    assert result[0]["original"] == "Olypics"
    mock_gemini_client.aio.models.generate_content.assert_called_once()


async def test_extract_parts_from_response():
    """Tests that parts are extracted from both the main list and artifacts."""
    response_data = {
        "parts": [{"text": "part 1"}],
        "artifacts": [
            {
                "parts": [{"text": "part 2"}]
            }
        ],
    }
    result = await _extract_parts_from_response(response_data)
    assert len(result) == 2
    assert result[0]["text"] == "part 1"
    assert result[1]["text"] == "part 2"


@patch(
    "broadcast_orchestrator.timeline_manager._parse_spelling_errors_from_text",
    new_callable=AsyncMock,
)
async def test_process_spelling_errors(mock_parser, mock_tool_context):
    """Tests the processing of parts to create spelling error events."""
    mock_parser.return_value = [{
        "original": "test",
        "suggestion": "Test",
        "context": "This is a test.",
    }]
    parts = [{"text": "some text"}]

    result = await _process_spelling_errors(parts, mock_tool_context)

    mock_parser.assert_called_once_with("some text")
    assert len(result) == 1
    assert result[0]["type"] == "SPELLING_ERROR"
    assert result[0]["details"]["original_word"] == "test"


async def test_process_video_clips():
    """Tests the processing of parts to create video clip events."""
    parts = [
        {"text": "not a file"},
        {
            "file": {
                "uri": "/video.mp4"
            },
            "metadata": {
                "title": "Test Video"
            },
        },
    ]
    result = await _process_video_clips(parts)
    assert len(result) == 1
    assert result[0]["type"] == "VIDEO_CLIP"
    assert result[0]["title"] == "Test Video"


async def test_save_timeline_events(mock_firestore_client, mock_tool_context):
    """Tests that events are correctly saved to Firestore."""
    events = [{"id": "event1"}, {"id": "event2"}]

    await _save_timeline_events(events, mock_tool_context)

    assert mock_firestore_client.collection.call_count == 2
    set_call = mock_firestore_client.collection.return_value.document.return_value.set
    assert set_call.call_count == 2
    # Check that user_id and session_id were added
    assert "user_id" in set_call.call_args_list[0][0][0]


# --- Integration-style Tests for the Orchestrator Function ---


@patch("broadcast_orchestrator.timeline_manager._save_timeline_events", new_callable=AsyncMock)
@patch("broadcast_orchestrator.timeline_manager._process_video_clips", new_callable=AsyncMock)
@patch("broadcast_orchestrator.timeline_manager._process_spelling_errors", new_callable=AsyncMock)
async def test_process_tool_output_orchestration_for_posture_agent(
    mock_process_spelling, mock_process_video, mock_save, mock_tool_context
):
    """Tests that the main function correctly orchestrates calls for the posture agent."""
    # Arrange
    mock_tool = MagicMock()
    mock_tool.name = "send_message"
    mock_args = {"agent_name": "Posture Agent"}
    
    mock_tool_response = [json.dumps({"text": "a part"})]

    mock_process_spelling.return_value = [{"id": "spell_event"}]
    mock_process_video.return_value = [{"id": "video_event"}]

    # Act
    await process_tool_output_for_timeline(
        tool=mock_tool, 
        tool_context=mock_tool_context, 
        args=mock_args,
        tool_response=mock_tool_response
    )

    # Assert
    mock_process_spelling.assert_called_once_with([{"text": "a part"}], mock_tool_context)
    mock_process_video.assert_called_once_with([{"text": "a part"}])
    mock_save.assert_called_once_with([{"id": "spell_event"}, {"id": "video_event"}], mock_tool_context)


@patch("broadcast_orchestrator.timeline_manager._save_timeline_events", new_callable=AsyncMock)
@patch("broadcast_orchestrator.timeline_manager._process_video_clips", new_callable=AsyncMock)
@patch("broadcast_orchestrator.timeline_manager._process_spelling_errors", new_callable=AsyncMock)
async def test_process_tool_output_orchestration_for_other_agent(
    mock_process_spelling, mock_process_video, mock_save, mock_tool_context
):
    """Tests that spelling check is skipped for other agents."""
    # Arrange
    mock_tool = MagicMock()
    mock_tool.name = "send_message"
    mock_args = {"agent_name": "Other Agent"}

    mock_tool_response = [json.dumps({"text": "a part"})]
    
    mock_process_video.return_value = []

    # Act
    await process_tool_output_for_timeline(
        tool=mock_tool, 
        tool_context=mock_tool_context, 
        args=mock_args,
        tool_response=mock_tool_response
    )

    # Assert
    mock_process_spelling.assert_not_called()  # The key assertion
    mock_process_video.assert_called_once_with([{"text": "a part"}])
    mock_save.assert_not_called()
