import os
import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv
from google.adk.tools.tool_context import ToolContext
import firebase_admin
from firebase_admin import firestore_async
import google.auth
from google import genai

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# Configure Gemini
gemini_client = None
location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'europe-west4')
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')

if project_id is None:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")

try:
    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
        logging.info("Gemini client configured with GEMINI_API_KEY.")
    else:
        gemini_client = genai.Client(vertexai=True,
                                     location=location,
                                     project=project_id)
        logging.info(
            "Gemini client configured using default credentials (e.g., GOOGLE_API_KEY or ADC)."
        )
except Exception as e:
    logging.error("Failed to configure Gemini client: %s", e, exc_info=True)


async def update_timeline_event_status(event_id: str, status: str) -> str:
    """
    Updates the status of a timeline event in Firestore.
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
    Uses a Gemini model to strictly parse a spelling report from another agent.
    """
    logger.info("Parsing potential spelling report with Gemini...")
    if not gemini_client:
        logger.error("Gemini client not initialized. Cannot parse.")
        return []
    try:
        prompt = '''
        You are a strict text parser. Your task is to analyze the following text, which is a report from a proofreading agent.
        Your job is to find all explicitly mentioned spelling or grammar corrections.
        For each correction, extract the original incorrect word/phrase, the suggested correction, and the full sentence that provides context.
        Return the result as a JSON array of objects. Each object must have the keys "original", "suggestion", and "context".
        If the text does not contain any explicit corrections, return an empty array.

        Example Input:
        "Okay, I\'ve reviewed the text and here are the corrections:

* \"Quen Elizabeth II in traditional Scottish attire with bapipes\" - This should be \"Queen Elizabeth II in traditional Scottish attire with bagpipes\".\n* \"Witer Olympics to be held in French Alps in 2031\" - This should be \"Winter Olympics to be held in French Alps in 2031\"."

        Example Output:
        [
            {
                "original": "Quen Elizabeth II in traditional Scottish attire with bapipes",
                "suggestion": "Queen Elizabeth II in traditional Scottish attire with bagpipes",
                "context": "Quen Elizabeth II in traditional Scottish attire with bapipes"
            },
            {
                "original": "Witer Olympics",
                "suggestion": "Winter Olympics",
                "context": "Witer Olympics to be held in French Alps in 2031"
            }
        ]
        '''

        full_prompt = f"{prompt}\n\nNow, parse the following text:\n---\n{text}"
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash-lite", contents=full_prompt)

        cleaned_response = response.text.strip().replace(
            "```json", "").replace("```", "").strip()

        if not cleaned_response or cleaned_response == "[]":
            return []

        errors = json.loads(cleaned_response)
        logger.info("Successfully parsed %d spelling errors from text.",
                    len(errors))
        return [e for e in errors if e.get("original") and e.get("suggestion")]

    except Exception as e:
        logger.error("Failed to parse spelling errors with Gemini: %s",
                     e,
                     exc_info=True)
        return []


async def _extract_parts_from_response(response_data: dict) -> list[dict]:
    """Extracts all parts from the agent response, including from artifacts."""
    all_parts = response_data.get("parts", [])
    if response_data.get("artifacts"):
        for artifact in response_data.get("artifacts"):
            all_parts.extend(artifact.get("parts", []))
    return all_parts


async def _process_spelling_errors(parts: list[dict],
                                   tool_context: ToolContext) -> list[dict]:
    """Processes a list of parts to find and format spelling error events."""
    events = []
    for part in parts:
        text_content = part.get("text")
        if not text_content:
            continue

        parsed_errors = await _parse_spelling_errors_from_text(text_content)
        if not parsed_errors:
            continue

        metadata = part.get("metadata", {})
        context_uid = metadata.get("uid") or metadata.get(
            "id") or metadata.get("context_uid")
        if not context_uid:
            context_uid = tool_context.state.get("last_checked_uid")
        if not context_uid:
            logger.warning(
                "Could not determine context_uid for a spelling error.")

        for error in parsed_errors:
            event_data = {
                "id": str(uuid.uuid4()),
                "type": "SPELLING_ERROR",
                "category": "CHECKS",
                "title": "Spelling Suggestion",
                "subtitle": f'In: "{error.get("context", "N/A")}"',
                "severity": "warning",
                "status": "pending",
                "timeOffsetSec": 0,
                "details": {
                    "original_word": error.get("original"),
                    "suggested_correction": error.get("suggestion"),
                    "context_uid": context_uid,
                }
            }
            events.append(event_data)
    return events

def infer_mime_type(filename: str | None) -> str:
    """Infers the MIME type from a filename based on its extension."""
    if not filename:
        return "application/octet-stream"

    filename = filename.lower()
    if filename.endswith(".mp4"):
        return "video/mp4"
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        return "image/jpeg"
    if filename.endswith(".png"):
        return "image/png"
    # Add other common types as needed
    
    return "application/octet-stream"

async def _process_media_clips(parts: list[dict]) -> list[dict]:
    """Processes a list of parts to find and format video and image clip events."""
    events = []
    file_parts_to_log = [p for p in parts if p.get("file") and p.get("file", {}).get("uri")]
    logger.info("Found %d file parts with URI to log. Transforming...",
                len(file_parts_to_log))

    for file_part in file_parts_to_log:
        logger.info("Processing file_part: %s", file_part)
        metadata = file_part.get("metadata", {})
        file_details = file_part.get("file", {})
        uri = file_details.get("uri")
        mime_type = file_details.get("mime_type", "")

        if not mime_type:
            filename = metadata.get("filename") or file_details.get("name")
            if not filename and uri:
                filename = os.path.basename(urlparse(uri).path)
            if filename:
                mime_type = infer_mime_type(filename)
                logger.info("Inferred mime_type as '%s' from filename '%s'", mime_type, filename)

        if mime_type.startswith("image/"):
            event_type = "IMAGE_CLIP"
            category = "IMAGE"
            title = metadata.get("title", "New Image")
            details = {"image_uri": uri, "mime_type": mime_type}
        elif mime_type.startswith("video/"):
            event_type = "VIDEO_CLIP"
            category = "VIDEO"
            title = metadata.get("title", "New Video Clip")
            thumbnail_uri = metadata.get("cover_url")
            details = {"video_uri": uri, "thumbnail_uri": thumbnail_uri, "mime_type": mime_type}
            if metadata.get("type") == "moment":
                details["tc_in"] = metadata.get("tc_in")
                details["tc_out"] = metadata.get("tc_out")
        else:
            logger.warning("Skipping file part with unknown mime_type: %s", mime_type)
            continue

        subtitle = metadata.get("description", "No description available.")

        event_data = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "category": category,
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
            logger.warning(
                "Could not find a source reference ID in file part metadata.")

        events.append(event_data)
        logger.info("Appended event: %s", event_data["type"])
    
    logger.info("Finished processing media clips. Total events created: %d", len(events))
    return events


async def _save_timeline_events(events: list[dict], tool_context: ToolContext):
    """Adds common metadata to events and saves them to Firestore."""
    user_id = tool_context.state.get("user_id", "unknown_user")
    session_id = tool_context.state.get("session_id", "unknown_session")
    db = firestore_async.client()

    tasks = []
    for event_data in events:
        event_data['user_id'] = user_id
        event_data['session_id'] = session_id
        event_data['timestamp'] = datetime.now(timezone.utc)
        doc_ref = db.collection("timeline_events").document(event_data['id'])
        tasks.append(doc_ref.set(event_data))

    logger.info("Preparing to write %d events to Firestore.", len(tasks))
    await asyncio.gather(*tasks)
    logger.info("Successfully saved %d timeline events to Firestore.",
                len(tasks))


async def process_tool_output_for_timeline(**kwargs):
    """
    Orchestrates processing of a tool call to generate timeline events.
    """
    logger.info("Processing tool output for timeline...")
    tool = kwargs.get("tool")
    tool_context = kwargs.get("tool_context")
    tool_response = kwargs.get("tool_response")
    args = kwargs.get("args", {})
    remote_agent_name = args.get("agent_name", "").lower()

    if not tool or not tool_context or tool.name != "send_message":
        return

    try:
        if not tool_response or not isinstance(tool_response, list):
            return

        # Pre-filter for items that look like JSON objects or arrays to avoid parse errors
        json_items = [
            item for item in tool_response 
            if isinstance(item, str) and item.strip().startswith(('{', '['))
        ]

        if not json_items:
            logger.info("No valid JSON items found in tool_response for timeline processing.")
            return

        all_parts = [json.loads(item) for item in json_items]
        all_events = []

        if "posture" in remote_agent_name:
            # If it is the posture agent it is checking for errors
            logger.info(
                "Posture agent response detected. Checking for spelling reports..."
            )
            spelling_events = await _process_spelling_errors(
                all_parts, tool_context)
            all_events.extend(spelling_events)

        media_events = await _process_media_clips(all_parts)
        logger.info("media_events created: %s", media_events)
        all_events.extend(media_events)

        if all_events:
            logger.info("Calling _save_timeline_events with %d events.", len(all_events))
            await _save_timeline_events(all_events, tool_context)
        else:
            logger.warning("No events were created, skipping save.")

    except Exception as e:
        logger.error("Error in process_tool_output_for_timeline: %s", e, exc_info=True)