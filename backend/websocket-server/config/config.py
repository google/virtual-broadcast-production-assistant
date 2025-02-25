'''
Configuration for Vertex AI Gemini Multimodal Live Proxy Server
'''

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CUEZ_AUTOMATOR_ENDPOINT = os.getenv('CUEZ_AUTOMATOR_ENDPOINT',
                                    'http://localhost:7070/api')


class ConfigurationError(Exception):
  '''Custom exception for configuration errors.'''
  pass


def get_secret(secret_id: str) -> str:
  '''Get secret from Secret Manager.'''
  client = secretmanager.SecretManagerServiceClient()
  project_id = os.environ.get('PROJECT_ID', 'heikohotz-genai-sa')

  if not project_id:
    raise ConfigurationError('PROJECT_ID environment variable is not set')

  secret_path = f'projects/{project_id}/secrets/{secret_id}/versions/latest'

  try:
    response = client.access_secret_version(request={'name': secret_path})
    return response.payload.data.decode('UTF-8')
  except Exception as e:
    logger.error('Failed to get secret from Secret Manager: %s', e)
    raise e


class ApiConfig:
  '''API configuration handler.'''

  def __init__(self):
    # Determine if using Vertex AI
    self.use_vertex = os.getenv('VERTEX_API', 'true').lower() == 'true'

    self.api_key: Optional[str] = None

    logger.info('Initialized API configuration with Vertex AI: %s',
                self.use_vertex)

  async def initialize(self):
    '''Initialize API credentials.'''

    if not self.use_vertex:
      try:
        self.api_key = get_secret('GOOGLE_API_KEY')
      except Exception as e:
        logger.warning('Failed to get API key from Secret Manager: %s', e)
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
          raise ConfigurationError(
              f'No API key available from Secret Manager or environment. {e}'
          ) from e


# Initialize API configuration
api_config = ApiConfig()

# Model configuration
if api_config.use_vertex:
  MODEL = os.getenv('MODEL_VERTEX_API', 'gemini-2.0-flash').strip()
  VOICE = os.getenv('VOICE_VERTEX_API', 'Aoede').strip()
else:
  MODEL = os.getenv('MODEL_DEV_API', 'models/gemini-2.0-flash')
  VOICE = os.getenv('VOICE_DEV_API', 'Puck')

logger.info('Using model: %s and voice: %s')

# Cloud Function URLs with validation
# TODO: This should be replaced with TOOL endpoints, they may not
# be cloud functions
TOOLS = {'cuez_automator': CUEZ_AUTOMATOR_ENDPOINT}

# Validate Cloud Function URLs
for name, url in TOOLS.items():
  if not url:
    logger.warning('Missing URL for cloud function: %s', name)
  elif not url.startswith('https://') and not url.startswith('http://'):
    logger.warning('Invalid URL format for %s: %s', name, url)

# Load system instructions
try:
  with open('config/system-instructions.txt', 'r', encoding='utf-8') as f:
    SYSTEM_INSTRUCTIONS = f.read()
except Exception as e:
  logger.error('Failed to load system instructions: %s', e)
  SYSTEM_INSTRUCTIONS = ''

# Load cuez swagger json
try:
  with open('config/cuez_api_swagger.json', 'r', encoding='utf-8') as f:
    SWAGGER_JSON = f.read()
    logger.info('SWAGGER_JSON %s', SWAGGER_JSON[:100] + '...[truncated]')
except Exception as e:
  logger.error('Failed to load cuez swagger json: %s', e)
  SWAGGER_JSON = ''

SYSTEM_INSTRUCTIONS = SYSTEM_INSTRUCTIONS.replace('$SWAGGER_JSON',
                                                  SWAGGER_JSON)

logger.info('System instructions: %s', SYSTEM_INSTRUCTIONS)

# Gemini Configuration
CONFIG = {
    'generation_config': {
        'response_modalities': ['AUDIO'],
        'speech_config': VOICE
    },
    'tools': [{
        'function_declarations': [{
            "name": "cuez_automator",
            "description":
            "A tool for querying the cuez automation system via API",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to use for the API call."
                    }
                },
                "required": ["path"]
            }
        }]
    }],
    'system_instruction':
    SYSTEM_INSTRUCTIONS
}
