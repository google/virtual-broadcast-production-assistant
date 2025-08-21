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
import os
import logging
import sys

import vertexai
from vertexai import agent_engines

import broadcast_orchestrator.agent as agent  # type: ignore

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

try:
    project = os.environ.get('GOOGLE_CLOUD_PROJECT')
    if project is None:
        raise Exception('No project set in environment')
    logger.info(f"Project: {project}")

    staging_buecket = os.environ.get('STORAGE_BUCKET')
    if staging_buecket is None:
        raise Exception('No staging bucket set.')
    logger.info(f"Staging bucket: {staging_buecket}")

    vertexai.init(project=project,
                  location=os.environ.get('GOOGLE_CLOUD_LOCATION',
                                          'europe-west4'),
                  staging_bucket=f'gs://{staging_buecket}')
    logger.info("Vertex AI initialized.")

    root_agent = agent.root_agent
    logger.info(f"Root agent name: {root_agent.name}")

    display_name = 'Orchestrater Agent'
    description = '''
        This is the agent responsible for choosing which remote agents to send
        tasks to and coordinate their work on helping user in the live broadcast
        control room
    '''

    logger.info("Creating agent engine...")
    remote_agent = agent_engines.create(
        root_agent,
        display_name=display_name,
        description=description,
        gcs_dir_name=staging_buecket,
        requirements='./requirements.txt',
        extra_packages=['broadcast_orchestrator'],
    )
    logger.info("Agent engine created.")

    # Let's inspect the remote_agent object to find the URL
    logger.info("--- Inspecting remote_agent object for URL ---")
    for attr in ['url', 'uri', 'endpoint', 'host', 'hostname', 'endpoints']:
        if hasattr(remote_agent, attr):
            logger.info(f"Found attribute '{attr}': {getattr(remote_agent, attr)}")
    logger.info("---------------------------------------------")

    with open("/workspace/resource_name.txt", "w") as f:
        f.write(remote_agent.resource_name)

    logger.info(f"Agent engine resource name: {remote_agent.resource_name}")

except Exception as e:
    logger.error(f"An error occurred: {e}")
    sys.exit(1)
