"""A tool for transforming and saving timeline events in a single step."""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from google.adk.tools.tool_context import ToolContext
import firebase_admin
from firebase_admin import firestore_async
import google.generativeai as genai


logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app()


async def update_timeline_event_status(event_id: str, status: str) -> str:
    """
    Updates the status of a timeline event in Firestore.

    Args:
        event_id: The ID of the event to update.
        status: The new status (e.g., 'corrected', 'acknowledged').

    Returns:
        A string indicating the result of the operation.
    """
    logger.info("Updating timeline event %s to status %s", event_id, status)
    try:
        db = firestore_async.client()
        doc_ref = db.collection("timeline_events").document(event_id)
        await doc_ref.update({"status": status})
        logger.info("Successfully updated status for event %s.", event_id)
        return f"Timeline event {event_id} status updated to {status}."
    except Exception as e:
        logger.error("Error in update_timeline_event_status: %s", e)
        return f"Failed to update status for event {event_id}: {e}"


async def _parse_spelling_errors_from_text(text: str) -> list[dict]:
    """
    Uses a Gemini model to parse a natural language string and extract spelling errors.

    Args:
        text: The text from the Posture Agent's response.

    Returns:
        A list of dictionaries, where each dictionary represents a spelling error.
        Returns an empty list if no errors are found or if parsing fails.
    """
    logger.info("Parsing text for spelling errors with Gemini...")
    try:
        # Using a fast model to minimize latency, as suggested.
        model = genai.GenerativeModel("gemini-1.5-flash-preview-0514")

        prompt = """
        You are an expert text parser. Analyze the following text and identify all instances where a word or phrase is marked as misspelled.
        Extract the original incorrect word/phrase, the suggested correction, and the full sentence that provides context.
        Return the result as a JSON array of objects. Each object must have the keys "original", "suggestion", and "context".
        If no misspellings are found, return an empty array. Do not return items that are marked as correct.

        Example input:
        "Okay, I've reviewed the text you provided. Here's what I found:\\n\\n*   \\"Winter Olypics to be held in French Alps in 2031\\" - \\"Olypics\\" is misspelled, it should be \\"Olympics\\".\\n\\n*   \\"Measles Outbreak at ITN\\" - This is correct."

        Example output:
        [
            {
                "original": "Olypics",
                "suggestion": "Olympics",
                "context": "Winter Olypics to be held in French Alps in 2031"
            }
        ]

        Now, parse the following text:
        ---
        """

        full_prompt = f"{prompt}\n{text}"
        # The API key should be configured globally for the application
        # or through environment variables (GOOGLE_API_KEY).
        response = await model.generate_content_async(full_prompt)

        # Clean up the response from markdown and parse JSON
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()

        if not cleaned_response or cleaned_response == "[]":
            logger.info("Gemini parsing returned no spelling errors.")
            return []

        errors = json.loads(cleaned_response)
        logger.info("Successfully parsed %d spelling errors from text.", len(errors))
        return [e for e in errors if e.get("original") and e.get("suggestion")]

    except json.JSONDecodeError as e:
        logger.error("Gemini returned invalid JSON: %s. Response text: %s", e, cleaned_response)
        return []
    except Exception as e:
        logger.error("Failed to parse spelling errors with Gemini: %s", e, exc_info=True)
        return []


async def process_tool_output_for_timeline(**kwargs):
    """
    Processes the output of a tool call, transforms relevant parts, and
    updates the timeline in Firestore.
    """
    logger.info("Processing tool output for timeline...")
    tool = kwargs.get("tool")
    tool_context = kwargs.get("tool_context")

    if not tool or not tool_context:
        logger.warning(
            "Could not process tool output: required context missing.")
        return

    if tool.name != "send_message":
        return

    logger.info(
        "'send_message' tool output detected. Parsing for timeline events."
    )
    try:
        full_a2a_response_string = tool_context.state.get(
            "last_a2a_response")
        if not full_a2a_response_string:
            logger.warning(
                "Could not find 'last_a2a_response' in tool context state."
            )
            return

        response_data = json.loads(full_a2a_response_string)
        all_parts = response_data.get("parts", [])
        if response_data.get("artifacts"):
            for artifact in response_data.get("artifacts"):
                all_parts.extend(artifact.get("parts", []))

        list_of_events = []

        # --- 1. Process Text Parts for Spelling Errors ---
        text_parts = [p.get("text") for p in all_parts if p.get("text")]
        for text_content in text_parts:
            # Heuristic to check if the text might contain spelling results
            if "misspelled" in text_content.lower() or "spelling" in text_content.lower():
                logger.info("Potential spelling report found. Parsing with Gemini...")
                parsed_errors = await _parse_spelling_errors_from_text(text_content)

                for error in parsed_errors:
                    # TODO: Find a real context_uid. Using a placeholder for now.
                    context_uid = tool_context.state.get("last_checked_uid", "uid-not-found")

                    event_data = {
                        "id": str(uuid.uuid4()),
                        "type": "SPELLING_ERROR",
                        "category": "CHECKS",
                        "title": "Spelling Suggestion",
                        "subtitle": f"In: \"{error.get('context', 'N/A')}\"",
                        "severity": "warning",
                        "status": "pending",
                        "timeOffsetSec": 0,
                        "details": {
                            "original_word": error.get("original"),
                            "suggested_correction": error.get("suggestion"),
                            "context_uid": context_uid,
                        }
                    }
                    list_of_events.append(event_data)

        # --- 2. Process File Parts for Video Clips ---
        file_parts_to_log = [p for p in all_parts if p.get("file")]
        if file_parts_to_log:
            logger.info(
                "Found %d file parts to log. Transforming...",
                len(file_parts_to_log))
            for file_part in file_parts_to_log:
                logger.info("Processing file part: %s", file_part)
                metadata = file_part.get("metadata", {})
                
                title = metadata.get("title", "New Video Clip")
                subtitle = metadata.get("description", "No description available.")
                video_uri = file_part.get("file", {}).get("uri")
                thumbnail_uri = metadata.get("cover_url")

                details = {
                    "video_uri": video_uri,
                    "thumbnail_uri": thumbnail_uri,
                }

                if metadata.get("type") == "moment":
                    details["tc_in"] = metadata.get("tc_in")
                    details["tc_out"] = metadata.get("tc_out")

                event_data = {
                    "id": str(uuid.uuid4()),
                    "type": "VIDEO_CLIP",
                    "category": "VIDEO",
                    "title": title,
                    "subtitle": subtitle,
                    "severity": "info",
                    "status": "default",
                    "timeOffsetSec": 0,
                    "details": details
                }

                source_ref_id = metadata.get("moment_id") or metadata.get("id")
                if source_ref_id:
                    event_data["source_agent_ref_id"] = source_ref_id
                else:
                    logger.warning("Could not find a source reference ID ('moment_id' or 'id') in file part metadata.")
                
                list_of_events.append(event_data)

        # --- 3. Save all collected events to Firestore ---
        if not list_of_events:
            logger.info("No timeline events were generated from the tool output.")
            return

        user_id = tool_context.state.get("user_id", "unknown_user")
        session_id = tool_context.state.get("session_id",
                                            "unknown_session")
        db = firestore_async.client()

        tasks = []
        for event_data in list_of_events:
            event_data['user_id'] = user_id
            event_data['session_id'] = session_id
            event_data['timestamp'] = datetime.now(timezone.utc)

            doc_ref = db.collection("timeline_events").document(
                event_data['id'])
            tasks.append(doc_ref.set(event_data))

        logger.info("Preparing to write %d events to Firestore.",
                    len(tasks))
        await asyncio.gather(*tasks)
        logger.info("Successfully saved %d timeline events to Firestore.",
                    len(tasks))

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error(
            "Failed to parse or process tool_output for timeline: %s",
            e,
            exc_info=True)
