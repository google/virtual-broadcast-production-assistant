import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "TX Stream Processor"
SECONDS_PER_REQUEST = 2  # Analyze roughly every 2 seconds
AUDIO_CHUNK_DURATION = 2  # Duration of audio to send with each request (seconds)
AUDIO_SAMPLE_RATE = 16000  # Sample rate for audio capture (Hz)
AUDIO_CHANNELS = 1  # Mono audio
AUDIO_BIT_DEPTH = 16  # Bits per sample

GEMINI_MODEL_FOR_AGENT = os.getenv("GEMINI_MODEL_FOR_AGENT", "gemini-2.0-flash-exp")
DB_COLLECTION_NAME = os.getenv("FIRESTORE_DB_COLLECTION", "broadcast_log_entries")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
STREAM_SSL_VERIFY = os.getenv("STREAM_SSL_VERIFY", "true").lower() == "true"
GOOGLE_EMBEDDING_MODEL = "text-embedding-004"

# Tags to use in firebase
VALID_TAGS = [
  "breaking",
  "economy",
  "education",
  "entertainment",
  "environment",
  "health",
  "opinion",
  "politics",
  "police",
  "sports",
  "technology",
  "world",
]
