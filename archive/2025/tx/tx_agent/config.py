import os
from dotenv import load_dotenv

load_dotenv()

DB_COLLECTION_NAME = os.getenv("FIRESTORE_DB_COLLECTION")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_EMBEDDING_MODEL = "text-embedding-004"
GEMINI_MODEL_FOR_AGENT = os.getenv("GEMINI_MODEL_FOR_AGENT", "gemini-2.5-flash")
TX_AGENT_API_KEY = os.getenv("TX_AGENT_API_KEY")

