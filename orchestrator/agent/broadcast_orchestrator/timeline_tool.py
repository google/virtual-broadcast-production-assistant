"""
Tools for interacting with the timeline and handling media assets.
"""
import asyncio
import json
import logging
import os
from firebase_admin import firestore_async
from .gcs_uploader import cache_asset_to_gcs, get_gcs_signed_url

logger = logging.getLogger(__name__)
db = firestore_async.client()

async def get_uri_by_source_ref_id(source_ref_id: str) -> str:
    """
    Retrieves a usable, short-lived URI for a media asset.

    This function implements a read-through cache. It first checks for a
    cached version of the asset in GCS.
    - If found, it returns a new signed URL for the GCS object.
    - If not found, it retrieves the original signed URL from the
      `timeline_events` collection, returns it for immediate use, and
      triggers a background task to cache the asset in GCS for future use.

    Args:
        source_ref_id: The ID of the asset from the source agent (e.g., Moments Lab ID).

    Returns:
        A JSON string containing the URI and mime_type, or an error message.
    """
    logger.info("Resolving URI for source_ref_id: %s", source_ref_id)
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not gcs_bucket_name:
        return "Error: GCS_BUCKET_NAME environment variable not set."

    try:
        # 1. Check for a cached asset in Firestore `media_assets` collection
        media_asset_ref = db.collection("media_assets").document(source_ref_id)
        cached_asset = await media_asset_ref.get()

        if cached_asset.exists:
            cached_data = cached_asset.to_dict()
            gcs_uri = cached_data.get("gcs_uri")
            mime_type = cached_data.get("mime_type", "application/octet-stream")
            logger.info("Found cached asset in GCS: %s", gcs_uri)
            
            signed_url = await get_gcs_signed_url(gcs_uri)
            if signed_url:
                return json.dumps({"uri": signed_url, "mime_type": mime_type})
            else:
                # Fallback to original URL if signed URL generation fails
                logger.warning("Failed to generate signed URL for GCS asset. Falling back.")

        # 2. If not cached, get the original URL from the timeline event
        logger.info("Asset not in GCS cache. Checking timeline_events.")
        events_ref = db.collection("timeline_events")
        query = events_ref.where("source_agent_ref_id", "==", source_ref_id).order_by("timestamp", direction="DESCENDING").limit(1)
        query_snapshot = await query.get()

        if not query_snapshot:
            logger.warning("No timeline event found with source_ref_id: %s", source_ref_id)
            return f"Error: No timeline event found with source_ref_id '{source_ref_id}'"

        event_data = query_snapshot[0].to_dict()
        details = event_data.get("details", {})
        original_uri = details.get("video_uri")
        mime_type = details.get("mime_type", "application/octet-stream")

        if not original_uri:
            logger.warning("No video_uri found for event with source_ref_id: %s", source_ref_id)
            return f"Error: No video_uri found for event with source_ref_id '{source_ref_id}'"

        # 3. Trigger background task to cache the asset (don't wait for it)
        logger.info("Triggering background task to cache asset: %s", source_ref_id)
        asyncio.create_task(
            cache_asset_to_gcs(
                source_url=original_uri,
                asset_id=source_ref_id,
                gcs_bucket_name=gcs_bucket_name
            )
        )

        # 4. Return the original URI for immediate use
        logger.info("Returning original URI for immediate use: %s", original_uri)
        return json.dumps({"uri": original_uri, "mime_type": mime_type})

    except Exception as e:
        logger.error("Error in get_uri_by_source_ref_id: %s", e, exc_info=True)
        return f"Error retrieving URI: {e}"