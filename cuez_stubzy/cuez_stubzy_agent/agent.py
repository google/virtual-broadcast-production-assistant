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

from google.adk.agents import LlmAgent


class CuezStubzyAgent:
  '''
    A class to represent the Cuez Stubzy Agent.
  '''

  SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

  def __init__(self):
    self._agent = self._build_agent()

  def _build_agent(self) -> LlmAgent:
    '''Builds the agent.'''

    return LlmAgent(
        model='gemini-2.5-flash-preview-05-20',
        name='root_agent',
        description=
        'An agent for interacting with the CUEZ rundown system and automator',
        instruction='Pretend you are a broadcast news room system',
    )
