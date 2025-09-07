"""
Module for handling Google Cloud Storage operations, including
downloading from a URL, uploading to a bucket, and managing
asset metadata in Firestore.
"""
import asyncio
import datetime
import logging
import os
import httpx
from firebase_admin import firestore_async
from google.cloud import storage
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client()
db = firestore_async.client()

async def cache_asset_to_gcs(
    source_url: str,
    asset_id: str,
    gcs_bucket_name: str
) -> None:
    """
    Downloads a file from a source URL and uploads it to GCS.
    After a successful upload, it updates Firestore with the asset's
    GCS location.

    Args:
        source_url: The public URL to download the asset from.
        asset_id: The unique ID for the asset (e.g., momentslab ID).
        gcs_bucket_name: The GCS bucket to upload the file to.
    """
    logger.info("Starting GCS cache for asset_id: %s", asset_id)
    try:
        # 1. Download the file from the source URL
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url, follow_redirects=True)
            response.raise_for_status()
            file_content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")

        # 2. Upload the file to Google Cloud Storage
        bucket = storage_client.bucket(gcs_bucket_name)
        # Use the asset_id as the GCS object name to ensure uniqueness
        blob = bucket.blob(asset_id)

        await asyncio.to_thread(blob.upload_from_string, file_content, content_type=content_type)
        gcs_uri = f"gs://{gcs_bucket_name}/{asset_id}"
        logger.info("Successfully uploaded asset %s to %s", asset_id, gcs_uri)

        # 3. Update Firestore with the new GCS URI
        media_asset_ref = db.collection("media_assets").document(asset_id)
        await media_asset_ref.set({
            "gcs_uri": gcs_uri,
            "source_url": source_url,
            "cached_at": firestore_async.SERVER_TIMESTAMP,
            "mime_type": content_type
        })
        logger.info("Successfully updated Firestore for asset_id: %s", asset_id)

    except httpx.HTTPStatusError as e:
        logger.error("HTTP error while downloading %s: %s", source_url, e)
    except Exception as e:
        logger.error("Failed to cache asset %s to GCS: %s", asset_id, e, exc_info=True)


async def get_gcs_signed_url(gcs_uri: str) -> str | None:
    """
    Generates a short-lived signed URL for a GCS object.

    Args:
        gcs_uri: The GCS URI of the object (e.g., gs://bucket/object).

    Returns:
        A signed URL string, or None if an error occurs.
    """
    try:
        # This will automatically use the service account credentials on Cloud Run
        credentials, project = await asyncio.to_thread(google.auth.default, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        
        # We need to refresh the credentials to get an access token.
        request = google.auth.transport.requests.Request()
        await asyncio.to_thread(credentials.refresh, request)

        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        expiration = datetime.timedelta(hours=1)
        
        signed_url = await asyncio.to_thread(
            blob.generate_signed_url,
            version="v4",
            expiration=expiration,
            service_account_email=credentials.service_account_email,
            access_token=credentials.token,
        )
        return signed_url
    except Exception as e:
        logger.error("Failed to generate signed URL for %s: %s", gcs_uri, e, exc_info=True)
        return None