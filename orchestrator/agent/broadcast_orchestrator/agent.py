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
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from broadcast_orchestrator.config import load_system_instructions

system_instructions = load_system_instructions()

logging.info(system_instructions)

root_agent = LlmAgent(
    name="broadcast_orchestrator_agent",
    model="gemini-2.0-flash-live-preview-04-09",
    description=("Agent to assist in the live news control room"),
    instruction=(str(system_instructions)),
    tools=[google_search],
)
