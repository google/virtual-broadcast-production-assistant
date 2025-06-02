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
import json

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
  DataPart,
  Part,
  Task,
  TaskState,
  TextPart,
  UnsupportedOperationError
)

from a2a.utils import (
  new_agent_parts_message,
  new_agent_text_message,
  new_task
)

from a2a.utils.errors import ServerError
from agent import CuezStubzyAgent

class CuezStubzyAgentExecutor(AgentExecutor):
  """Executor for the CuezStubzyAgent."""
  def __init__(self):
    self.agent = CuezStubzyAgent()

  async def execute(
    self,
    context: RequestContext,
    event_queue: EventQueue
  ) -> None:
    query = context.get_user_input()
    task = context.current_task
