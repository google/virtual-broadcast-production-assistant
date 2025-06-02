"""
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """
import logging
import os

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a.types import (
  AgentCapabilities,
  AgentCard,
  AgentSkill
)
from dotenv import load_dotenv
from agent import CuezStubzyAgent
from agent_executor import CuezStubzyAgentExecutor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass

@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10002)
def main(host, port):
  '''Main a2a entrypoint'''
  try:

    #TODO: Auth???

    if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
      if not os.getenv('GOOGLE_API_KEY'):
        raise MissingAPIKeyError(
            'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
      id="cuez_stubzy",
      name="Cuez Stubzy Tool",
      description="A tool for interacting with the CUEZ rundown system and automator",
      tags=['cuez','ncrs'],
      examples=[
        'What\'s in my show today?',
        'What is the next item in the rundown?',
        'How long is the current item in the rundown?',
        'What is the status of the teleprompter?',
        'Can you swap item 2 with Item 4?'
      ]
    )
    agent_card = AgentCard(
      name="Cuez Stubzy Agent",
      skills=[skill],
      capabilities=capabilities,
      description="An agent for interacting with the CUEZ rundown system and automator",
      defaultInputModes=CuezStubzyAgent.SUPPORTED_CONTENT_TYPES,
      defaultOutputModes=CuezStubzyAgent.SUPPORTED_CONTENT_TYPES,
      url=f'http://{host}:{port}/',
      version='0.0.1',
    )

    request_handler = DefaultRequestHandler(
      agent_executor=CuezStubzyAgentExecutor,
      task_store=InMemoryTaskStore()
    )

    server = A2AStarletteApplication(
      agent_card=agent_card, http_handler=request_handler
    )

    import uvicorn

    uvicorn.run(server.build(), host=host, port=port)

  except MissingAPIKeyError as e:
    logger.error(e)
    exit(1)
  except Exception as e:
    logger.error('An unexpected error occurred: %s', e)
    exit(1)

if __name__ == '__main__':
  main()
