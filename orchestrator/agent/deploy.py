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
from main import app
import vertexai
from vertexai import agent_engines

project = os.environ.get('GOOGLE_CLOUD_PROJECT')

if project is None:
  raise Exception('No project set in environment')

staging_buecket = os.environ.get('STAGING_BUCKET')

if staging_buecket is None:
  raise Exception('No staging bucket set.')

vertexai.init(staging_bucket=f'gs://{staging_buecket}')



display_name = 'Orchestrater Agent'

description = '''
    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work on helping user in the live broadcast
    control room
'''

remote_agent = agent_engines.create(
    app,
    display_name=display_name,
    description=description,
    gcs_dir_name=staging_buecket,
    requirements='requirements.txt',
)
