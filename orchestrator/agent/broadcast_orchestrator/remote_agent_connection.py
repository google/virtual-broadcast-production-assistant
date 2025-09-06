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

from typing import Callable

import httpx

from a2a.client import A2AClient
from a2a.types import (
    SendMessageResponse,
    SendMessageRequest,
    AgentCard,
    Task,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)

logger = logging.getLogger(__name__)

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self,
                 agent_card: AgentCard,
                 agent_url: str,
                 api_key: str | None = None):
        """Initializes a connection to a remote agent.

        Args:
            agent_card: The agent card of the remote agent.
            agent_url: The URL of the remote agent.
            api_key: The API key for the remote agent, if required.
        """

        logger.info("agent_url: %s", agent_url)
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
            logger.info("Using API Key for agent: %s", agent_card.name)

        self._httpx_client = httpx.AsyncClient(timeout=100, headers=headers)
        self.agent_client = A2AClient(self._httpx_client,
                                      agent_card,
                                      url=agent_url)
        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        """Returns the agent card for this connection."""
        return self.card

    async def send_message(
            self, message_request: SendMessageRequest) -> SendMessageResponse:
        """Sends a message to the remote agent.

        Args:
            message_request: The request object to send to the agent.

        Returns:
            The response from the agent.
        """
        return await self.agent_client.send_message(message_request)
