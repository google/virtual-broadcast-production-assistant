"""
Tools for interacting with the timeline and handling media assets.
"""
import json
import logging
from firebase_admin import firestore_async

logger = logging.getLogger(__name__)
db = firestore_async.client()

async def get_uri_by_source_ref_id(source_ref_id: str) -> str | None:
    """
    Retrieves a usable URI for a media asset.

    It retrieves the original signed URL from the
    `timeline_events` collection.

    Args:
        source_ref_id: The ID of the asset from the source agent (e.g., Moments Lab ID).

    Returns:
        A JSON string containing the URI and mime_type, or None if not found.
    """
    logger.info("Resolving URI for source_ref_id: %s", source_ref_id)

    try:
        # Get the original URL from the timeline event
        logger.info("Checking timeline_events for asset.")
        events_ref = db.collection("timeline_events")
        query = events_ref.where("source_agent_ref_id", "==", source_ref_id).order_by("timestamp", direction="DESCENDING").limit(1)
        query_snapshot = await query.get()

        if not query_snapshot:
            logger.warning("No timeline event found with source_ref_id: %s", source_ref_id)
            return None

        event_data = query_snapshot[0].to_dict()
        details = event_data.get("details", {})
        original_uri = details.get("video_uri")
        mime_type = details.get("mime_type", "application/octet-stream")

        if not original_uri:
            logger.warning("No video_uri found for event with source_ref_id: %s", source_ref_id)
            return None

        # Return the original URI for immediate use
        logger.info("Returning original URI for immediate use: %s", original_uri)
        return json.dumps({"uri": original_uri, "mime_type": mime_type})

    except Exception as e:
        logger.error("Error in get_uri_by_source_ref_id: %s", e, exc_info=True)
        return None

async def get_uri_by_title(title: str, session_id: str) -> str | None:
    """
    Retrieves a URI from a timeline event by matching the asset title and session ID.
    """
    logger.info("Resolving URI for title: '%s' in session: %s", title, session_id)
    try:
        events_ref = db.collection("timeline_events")
        query = events_ref.where("session_id", "==", session_id).where("title", ">=", title).where("title", "<", title + "\uf8ff").order_by("title").order_by("timestamp", direction="DESCENDING").limit(1)
        query_snapshot = await query.get()

        if not query_snapshot:
            logger.warning("No timeline event found with title: %s", title)
            return None

        event_data = query_snapshot[0].to_dict()
        details = event_data.get("details", {})
        return json.dumps(details) # Return the whole details dict
    except Exception as e:
        logger.error("Error in get_uri_by_title: %s", e)
        return None