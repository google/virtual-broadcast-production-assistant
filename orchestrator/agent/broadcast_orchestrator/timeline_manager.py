"""A tool for transforming and saving timeline events in a single step."""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from google.adk.tools.tool_context import ToolContext
import firebase_admin
from firebase_admin import firestore_async

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

    if tool.name == "send_message":
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

            file_parts_to_log = [p for p in all_parts if p.get("file")]

            if not file_parts_to_log:
                logger.info("No file parts found to log to timeline.")
                return

            logger.info(
                "Found %d file parts to log. Transforming in Python...",
                len(file_parts_to_log))

            list_of_events = []
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
                list_of_events.append(event_data)

            # --- Save all events to Firestore concurrently ---
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
