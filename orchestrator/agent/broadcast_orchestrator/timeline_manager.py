import os
import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
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
        prompt = """
        You are a strict text parser. Your task is to analyze the following text, which is a report from a proofreading agent.
        Your job is to find all explicitly mentioned spelling or grammar corrections.
        For each correction, extract the original incorrect word/phrase, the suggested correction, and the full sentence that provides context.
        Return the result as a JSON array of objects. Each object must have the keys "original", "suggestion", and "context".
        If the text does not contain any explicit corrections, return an empty array.

        Example Input:
        "Okay, I've reviewed the text and here are the corrections:\n\n* \"Quen Elizabeth II in traditional Scottish attire with bapipes\" - This should be \"Queen Elizabeth II in traditional Scottish attire with bagpipes\".\n* \"Witer Olympics to be held in French Alps in 2031\" - This should be \"Winter Olympics to be held in French Alps in 2031\"."

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
        ]"""

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


async def process_tool_output_for_timeline(**kwargs):
    """
    Processes the output of a tool call, transforms relevant parts, and
    updates the timeline in Firestore.
    """
    logger.info("Processing tool output for timeline...")
    tool = kwargs.get("tool")
    tool_context = kwargs.get("tool_context")
    remote_agent_name = None
    args = kwargs.get("args")
    if args:
        remote_agent_name = args.get("agent_name").lower()

    if not tool or not tool_context:
        logger.warning(
            "Could not process tool output: required context missing.")
        return

    if tool.name != "send_message":
        return

    try:
        full_a2a_response_string = tool_context.state.get("last_a2a_response")
        if not full_a2a_response_string:
            return

        response_data = json.loads(full_a2a_response_string)
        all_parts = response_data.get("parts", [])
        if response_data.get("artifacts"):
            for artifact in response_data.get("artifacts"):
                all_parts.extend(artifact.get("parts", []))

        list_of_events = []

        # Check if the response is from the posture agent before processing for spelling.
        if "posture" in remote_agent_name:
            logger.info(
                "Posture agent response detected. Parsing for spelling reports..."
            )
            for part in all_parts:
                text_content = part.get("text")
                if not text_content:
                    continue

                parsed_errors = await _parse_spelling_errors_from_text(
                    text_content)

                if not parsed_errors:
                    continue

                metadata = part.get("metadata", {})
                logging.info(metadata)
                context_uid = metadata.get("uid") or metadata.get(
                    "id") or metadata.get("context_uid")

                if not context_uid:
                    context_uid = tool_context.state.get("last_checked_uid")

                if not context_uid:
                    logger.warning(
                        "Could not determine context_uid for a spelling error from metadata or chat state."
                    )

                for error in parsed_errors:
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

        # Video clip processing can run for any agent
        file_parts_to_log = [p for p in all_parts if p.get("file")]
        if file_parts_to_log:
            logger.info("Found %d file parts to log. Transforming...",
                        len(file_parts_to_log))
            for file_part in file_parts_to_log:
                logger.info("Processing file part: %s", file_part)
                metadata = file_part.get("metadata", {})

                title = metadata.get("title", "New Video Clip")
                subtitle = metadata.get("description",
                                        "No description available.")
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
                    logger.warning(
                        "Could not find a source reference ID ('moment_id' or 'id') in file part metadata."
                    )

                list_of_events.append(event_data)

        if not list_of_events:
            return

        user_id = tool_context.state.get("user_id", "unknown_user")
        session_id = tool_context.state.get("session_id", "unknown_session")
        db = firestore_async.client()

        tasks = []
        for event_data in list_of_events:
            event_data['user_id'] = user_id
            event_data['session_id'] = session_id
            event_data['timestamp'] = datetime.now(timezone.utc)
            doc_ref = db.collection("timeline_events").document(
                event_data['id'])
            tasks.append(doc_ref.set(event_data))

        logger.info("Preparing to write %d events to Firestore.", len(tasks))
        await asyncio.gather(*tasks)
        logger.info("Successfully saved %d timeline events to Firestore.",
                    len(tasks))

    except Exception as e:
        logger.error("Error in process_tool_output_for_timeline: %s",
                     e,
                     exc_info=True)
