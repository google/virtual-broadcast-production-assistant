"""Module for the Routing Agent."""
import asyncio
from urllib.parse import urlparse
import json
import os
import logging
import uuid
from typing import Any, List
from dotenv import load_dotenv
import httpx
from a2a.client import A2ACardResolver
from a2a.types import (AgentCard, MessageSendParams, Part, SendMessageRequest,
                       SendMessageResponse, SendMessageSuccessResponse, Task,
                       TextPart, Message)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from google.genai.types import GenerateContentConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig

from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from .config import load_system_instructions

load_dotenv()

logger = logging.getLogger("orchestartor::routing_agent" + __name__)


def convert_part(part: Part):
    """Converts an A2A Part to a string."""
    # Currently only support text parts
    if isinstance(part.root, TextPart):
        return part.root.text

    return f"Unknown type: {type(part.root)}"


def convert_parts(parts: list[Part]):
    """Converts a list of A2A Parts to a list of strings."""
    rval = []
    for p in parts:
        rval.append(convert_part(p))
    return rval


def create_send_message_payload(
        text: str,
        task_id: str | None = None,
        context_id: str | None = None) -> dict[str, Any]:
    """Helper function to create the payload for sending a task."""
    payload: dict[str, Any] = {
        "message": {
            "role": "user",
            "parts": [{
                "type": "text",
                "text": text
            }],
            "messageId": uuid.uuid4().hex,
        },
    }

    if task_id:
        payload["message"]["taskId"] = task_id

    if context_id:
        payload["message"]["contextId"] = context_id
    return payload


class RoutingAgent:
    """The Routing agent.

    This is the agent responsible for choosing which remote seller agents to
    send tasks to and coordinate their work.
    """

    def __init__(
        self,
        task_callback: TaskUpdateCallback | None = None,
    ):
        """Initializes the RoutingAgent."""
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        """Asynchronously initializes components that require network I/O."""
        # Use a single httpx.AsyncClient for all card resolutions for
        # efficiency
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    card: AgentCard = await card_resolver.get_agent_card()
                    logger.info(card)
                    # The remote agent card might contain a non-routable URL
                    # (e.g., http://0.0.0.0:port). We should prioritize the public
                    # address we used for discovery.
                    card_url_parts = urlparse(card.url)
                    if card_url_parts.hostname in ("0.0.0.0", "localhost",
                                                   "127.0.0.1"):
                        logger.warning(
                            "Remote agent '%s' has a non-routable URL '%s'. "
                            "Correcting it to use the discovery address '%s'.",
                            card.name, card.url, address)
                        card.url = address

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=card.url)
                    self.remote_agent_connections[
                        card.name] = remote_connection
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    logger.error("Failed to get agent card from %s: %s",
                                 address, e)
                # Catch other potential errors
                except Exception as e:
                    logger.error("Failed to initialize connection for %s: %s",
                                 address, e)

        # Populate self.agents using the logic from original __init__ (via
        # list_remote_agents)
        agent_info = []
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents = "\n".join(agent_info)

    async def _async_init_if_needed(self):
        """Initializes the agent's async components if not already done."""
        async with self._init_lock:
            if self._initialized:
                return
            # Get the base URL for the agent from environment variables.
            cuez_agent_url = os.getenv("CUEZ_AGENT_URL",
                                       "http://localhost:8001")
            posture_url = os.getenv("POSTURE_AGENT_URL",
                                    "http://localhost:10002")
            momentslab_url = os.getenv("MOMENTSLAB_AGENT_URL",
                                       "http://localhost:10003")
            remote_agent_addresses = [
                cuez_agent_url, momentslab_url, posture_url
            ]
            await self._async_init_components(remote_agent_addresses)
            self._initialized = True

    def create_agent(self) -> Agent:
        """Creates the ADK Agent instance."""
        system_instructions = load_system_instructions()
        # You can not seem to send any speechConfig along with ADK Live requests
        # speech_config = {
        #     # To adjust the speed of the voice, use 'speechRate'.
        #     # The value is a number between 0.25 and 4.0, where 1.0 is the default speed.
        #     "speechRate": 1.2,  # Example: 20% faster

        #     # To change the voice, use 'voiceConfig'.
        #     "voiceConfig": {
        #         # For standard voices, use 'prebuiltVoiceConfig'.
        #         "prebuiltVoiceConfig": {
        #             # Specify the voice name here.
        #             # Valid voices include: Zephyr, Puck, Kore, Fenrir, Leda, Orus, etc.
        #             "voiceName": "Puck",
        #         },
        #     },
        # }
        voice_config = VoiceConfig(prebuilt_voice_config=PrebuiltVoiceConfig(
            voice_name="Fenrir"))
        speech_config = SpeechConfig(voice_config=voice_config,
                                     language_code="en-GB")

        generate_content_config = GenerateContentConfig(
            speech_config=speech_config)

        return Agent(
            model="gemini-live-2.5-flash",
            name="Routing_agent",
            instruction=system_instructions,
            before_agent_callback=self.before_agent_callback,
            before_model_callback=self.before_model_callback,
            description=(
                "This Routing agent orchestrates requests for the user "
                "to assist in live news or sports broadcast control"),
            generate_content_config=generate_content_config,
            tools=[
                self.send_message,
            ],
        )

    def check_active_agent(self, context: ReadonlyContext):
        """Checks for an active agent session in the context."""
        state = context.state
        if ("session_id" in state and "session_active" in state
                and state["session_active"] and "active_agent" in state):
            return {"active_agent": f"{state['active_agent']}"}
        return {"active_agent": "None"}

    async def before_agent_callback(self, callback_context: CallbackContext,
                                    **kwargs):
        """A callback executed before the agent is called."""
        await self._async_init_if_needed()
        logger.info("before_agent_callback called %s", callback_context)

    async def before_model_callback(self, callback_context: CallbackContext,
                                    **kwargs):
        """A callback executed before the model is called."""
        await self._async_init_if_needed()
        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.cards:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            logger.info("Found agent card: %s",
                        card.model_dump(exclude_none=True))
            logger.info("=" * 100)
            remote_agent_info.append({
                "name": card.name,
                "description": card.description
            })
        return remote_agent_info

    async def send_message(self, agent_name: str, task: str,
                           tool_context: ToolContext) -> list[str]:
        """Sends a task to remote seller agent

        This will send a message to the remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to.
            task: The comprehensive conversation context summary and goal to be
                achieved regarding user inquiry and purchase request.
            tool_context: The tool context this method runs in.

        Returns:
            A list of parts from the remote agent's response.
        """
        await self._async_init_if_needed()
        if agent_name not in self.remote_agent_connections:
            error_message = (f"Error: Agent '{agent_name}' not found. "
                             "Available agents are: "
                             f"{list(self.remote_agent_connections.keys())}")
            logger.error(error_message)
            return [error_message]
        state = tool_context.state
        state["active_agent"] = agent_name
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")

        task_id = state.get("task_id", str(uuid.uuid4()))
        state["task_id"] = task_id  # Ensure task_id is stored in state

        context_id = state.get("context_id", str(uuid.uuid4()))
        state["context_id"] = context_id

        message_id = str(uuid.uuid4())
        if "input_message_metadata" in state:
            if "message_id" in state["input_message_metadata"]:
                message_id = state["input_message_metadata"]["message_id"]

        payload = create_send_message_payload(task, task_id, context_id)
        payload["message"]["messageId"] = message_id

        try:
            message_request = SendMessageRequest(
                id=message_id,
                params=MessageSendParams.model_validate(payload))
            send_response: SendMessageResponse = await client.send_message(
                message_request=message_request)
        except httpx.ConnectError as e:
            error_message = (
                "Network connection failed when trying to reach agent "
                f"'{agent_name}'. Please ensure the agent is running and "
                "accessible.")
            logger.error("ERROR: %s Details: %s", error_message, e)
            return [error_message]
        logger.info("send_response %s", send_response)

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            logger.warning("received non-success response. Aborting get task ")
            return ["Failed to send message."]

        result = send_response.root.result

        # Check if the result is a Task or a Message
        if not isinstance(result, (Task, Message)):
            logger.warning("received unexpected response. Aborting get task ")
            return [
                "Received an unexpected response type: %s" % str(type(result))
            ]
        response = send_response
        if hasattr(response, "root"):
            content = response.root.model_dump_json(exclude_none=True)
        else:
            content = response.model_dump(mode="json", exclude_none=True)

        resp = []
        json_content = json.loads(content)
        logger.info(json_content)
        if json_content.get("result") and json_content["result"].get(
                "artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(
                        convert_parts([
                            Part.model_validate(p) for p in artifact["parts"]
                        ]))
        elif json_content.get("result") and json_content["result"].get(
                "parts"):
            # Handle the case where the result is a Message
            resp.extend(
                convert_parts([
                    Part.model_validate(p)
                    for p in json_content["result"]["parts"]
                ]))
        return resp


# Create the agent instance synchronously.
# The async initialization will be handled lazily on the first call.
routing_agent_instance = RoutingAgent()
root_agent = routing_agent_instance.create_agent()
