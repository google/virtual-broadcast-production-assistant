"""
Gemini client initialization and connection management
"""

import logging
import os
from google import genai
from config.config import MODEL, CONFIG, api_config, ConfigurationError

logger = logging.getLogger(__name__)

async def create_gemini_session():
  """Create and initialize the Gemini client and session"""
  try:
    # Initialize authentication
    await api_config.initialize()

    if api_config.use_vertex:
      # Vertex AI configuration
      location = os.getenv('VERTEX_LOCATION', 'us-central1')
      project_id = os.environ.get('PROJECT_ID')

      if not project_id:
        raise ConfigurationError("PROJECT_ID is required for Vertex AI")

      logger.info(
          f"Initializing Vertex AI client with location: {location}, project: {project_id}"
      )

      # Initialize Vertex AI client
      client = genai.Client(
          vertexai=True,
          location=location,
          project=project_id,
          # http_options={'api_version': 'v1beta'}
      )
      logger.info("Vertex AI client initialized with client: %s", client)
    else:
      # Development endpoint configuration
      logger.info("Initializing development endpoint client")

      # Initialize development client
      client = genai.Client(vertexai=False,
                            http_options={'api_version': 'v1alpha'},
                            api_key=api_config.api_key)
    logger.info('Connecting to session with model: %s and config: %s', MODEL,
                CONFIG)
    # Create the session
    session = client.aio.live.connect(model=MODEL, config=CONFIG)
    logger.info("Gemini session created with session: %s", session)
    return session
  except ConfigurationError as e:
    logger.error(
        f"Configuration error while creating Gemini session: {str(e)}")
    raise
  except Exception as e:
    logger.error(f"Unexpected error while creating Gemini session: {str(e)}")
    raise
