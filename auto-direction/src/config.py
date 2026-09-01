import os
import google.auth
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Check if we have ADC credentials available as a fallback/alternative to API Key
has_adc = False
google_project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")

try:
    credentials, project_id = google.auth.default()
    if credentials:
        has_adc = True
        if not google_project_id and project_id:
            google_project_id = project_id
            # Set environment variable so standard GCP SDKs and google-genai detect it
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    pass

if GEMINI_API_KEY:
    GEMINI_MODEL = "gemini-2.5-flash-live"  # Using Live model for real-time WebSockets voice and vision
else:
    # Build fully qualified Vertex AI path using ADC
    if google_project_id:
        GEMINI_MODEL = f"projects/{google_project_id}/locations/us-central1/publishers/google/models/gemini-2.5-flash-live"
    else:
        GEMINI_MODEL = "gemini-2.5-flash-live"  # Fallback


# Network Ports
CUEZ_AUTOMATOR_PORT = 8000
WEBMCP_BRIDGE_PORT = 8001

# Source Metadata for PTZ & Pixel 11
AVAILABLE_SOURCES = {
    "cam_1": {"id": "cam_1", "name": "PTZ Camera - Wide Studio", "type": "ptz", "status": "active"},
    "cam_2": {"id": "cam_2", "name": "PTZ Camera - Host Focus", "type": "ptz", "status": "active"},
    "pixel_11": {"id": "pixel_11", "name": "Pixel 11 - Guest Mobile Mount", "type": "mobile_mount", "status": "active"},
}
