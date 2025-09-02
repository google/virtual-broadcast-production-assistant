"""Tools for interacting with the timeline."""
import logging
import firebase_admin
from firebase_admin import firestore_async

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    firebase_admin.initialize_app()

async def get_uri_by_source_ref_id(source_ref_id: str) -> str:
    """
    Retrieves a video URI from a timeline event in Firestore using the source agent's reference ID.

    Args:
        source_ref_id: The ID of the event from the source agent.

    Returns:
        The video URI string if found, otherwise an error message.
    """
    logger.info("Attempting to retrieve URI for source_ref_id: %s", source_ref_id)
    try:
        db = firestore_async.client()
        events_ref = db.collection("timeline_events")
        query = events_ref.where("source_agent_ref_id", "==", source_ref_id).limit(1)
        query_snapshot = await query.get()

        if not query_snapshot:
            logger.warning("No timeline event found with source_ref_id: %s", source_ref_id)
            return f"Error: No timeline event found with source_ref_id '{source_ref_id}'"

        document = query_snapshot[0]
        event_data = document.to_dict()
        video_uri = event_data.get("details", {}).get("video_uri")

        if not video_uri:
            logger.warning("No video_uri found in details for event with source_ref_id: %s", source_ref_id)
            return f"Error: No video_uri found for event with source_ref_id '{source_ref_id}'"

        logger.info("Successfully retrieved video_uri: %s", video_uri)
        return video_uri

    except Exception as e:
        logger.error("Error in get_uri_by_source_ref_id: %s", e, exc_info=True)
        return f"Error retrieving URI: {e}"
