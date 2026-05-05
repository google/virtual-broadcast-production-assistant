"""
Module for handling Google Cloud Storage uploads.
"""
import base64
import logging
import os
import uuid
import datetime
from urllib.parse import quote
from firebase_admin import storage

logger = logging.getLogger(__name__)

async def upload_base64_image_to_gcs(base64_data: str, filename: str) -> str | None:
    """
    Uploads a base64 encoded image to Firebase Storage and returns a token-based
    download URL.

    Args:
        base64_data: The base64 encoded image data.
        filename: The desired filename for the image in storage.

    Returns:
        The token-based download URL of the uploaded image, or None on failure.
    """
    try:
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not bucket_name:
            logger.error("GCS_BUCKET_NAME environment variable not set.")
            return None
        bucket = storage.bucket(bucket_name)
        image_data = base64.b64decode(base64_data)
        
        blob_name = f"images/{uuid.uuid4()}-{filename}"
        blob = bucket.blob(blob_name)

        # Generate a download token and set it in the custom metadata.
        download_token = uuid.uuid4()
        metadata = {"firebaseStorageDownloadTokens": str(download_token)}
        blob.metadata = metadata

        # Upload the file with the metadata.
        blob.upload_from_string(image_data, content_type="image/png")

        # Manually construct the download URL.
        encoded_blob_name = quote(blob.name, safe='')
        url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_blob_name}?alt=media&token={download_token}"
        
        logger.info("Successfully uploaded image %s to GCS. URL: %s", filename, url)
        return url

    except Exception as e:
        logger.error("Failed to upload base64 image to GCS: %s", e, exc_info=True)
        return None