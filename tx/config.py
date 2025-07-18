import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "LiveCast Analyst"
SECONDS_PER_REQUEST = 2  # Analyze roughly every 2 seconds
AUDIO_CHUNK_DURATION = 2  # Duration of audio to send with each request (seconds)
AUDIO_SAMPLE_RATE = 16000  # Sample rate for audio capture (Hz)
AUDIO_CHANNELS = 1  # Mono audio
AUDIO_BIT_DEPTH = 16  # Bits per sample

DB_COLLECTION_NAME = os.getenv("FIRESTORE_DB_COLLECTION")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
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
