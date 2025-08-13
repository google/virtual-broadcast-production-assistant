"""Module for the Routing Agent."""
import asyncio
from urllib.parse import urlparse
import json
import os
import logging
import uuid
from typing import Any
from dotenv import load_dotenv
import httpx
from a2a.client import A2ACardResolver
from a2a.client.errors import A2AClientTimeoutError
from a2a.types import (
    AgentCard,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TextPart,
    Message,
)
from google.cloud import firestore
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext


from .automation_system_instructions import (
    AUTOMATION_SYSTEMS,
    CUEZ_CONFIG,
    DEFAULT_INSTRUCTIONS,
    SOFIE_CONFIG,
)

from .config import (load_remote_agents_config, load_system_instructions)
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback

load_dotenv()

logger = logging.getLogger(__name__)


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
            "parts": [
                {
                    "type": "text",
                    "text": text
                }
            ],
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
        self._agent: Agent | None = None

    async def _load_agent(
            self, address: str,
            api_key: str | None) -> RemoteAgentConnections | None:
        """Loads a single remote agent and returns its connection object."""
        logger.info("Attempting to connect to remote agent at: %s", address)
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            card_resolver = A2ACardResolver(client, address)
            try:
                card: AgentCard = await card_resolver.get_agent_card()
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

                return RemoteAgentConnections(agent_card=card,
                                              agent_url=card.url,
                                              api_key=api_key)
            except httpx.ConnectError as e:
                logger.error("Failed to get agent card from %s: %s", address,
                             e)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    logger.error(
                        "Authentication error for agent at %s. Check if the API key is correct. Status: %s",
                        address, e.response.status_code)
                else:
                    logger.error("HTTP error for agent at %s: %s", address, e)
            except Exception as e:
                logger.error("Failed to initialize connection for %s: %s",
                             address, e)

        return None

    async def _async_init_components(
            self,
            remote_agents_config: dict[str,
                                     str | None]):
        """Asynchronously initializes components that require network I/O."""
        logger.info("Initializing remote agent connections...")
        for address, api_key in remote_agents_config.items():

            connection = await self._load_agent(address, api_key)
            if connection:
                self.remote_agent_connections[
                    connection.card.name] = connection
                self.cards[connection.card.name] = connection.card
        logger.info("Loaded %d remote agent cards.", len(self.cards))
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
            agent_configs = load_remote_agents_config()


            rundown_agent_config_names = {
                config['config_name']
                for config in AUTOMATION_SYSTEMS.values()
            }

            remote_agents_config = {}
            for config in agent_configs:
                if config["name"] in rundown_agent_config_names:
                    continue

                agent_name = config["name"]
                url = os.getenv(config["url_env"], config["default_url"])
                api_key = os.getenv(config["key_env"])
                if api_key:
                    logger.info('API KEY FOUND for %s', agent_name)
                else:
                    logger.info('No API KEY for %s', agent_name)
                if url:
                    remote_agents_config[url] = api_key

            logger.info("Remote agents to load: %s", remote_agents_config)
            await self._async_init_components(remote_agents_config)
            self._initialized = True

    def get_agent(self) -> Agent:
        """Creates and returns the ADK Agent instance if it doesn't exist."""
        if self._agent:
            return self._agent

        # Load the base instructions. The placeholders will be filled in
        # before each turn in the before_agent_callback.
        initial_instructions = load_system_instructions()

        self._agent = Agent(
            model="gemini-live-2.5-flash",
            name="Routing_agent",
            instruction=initial_instructions,
            before_agent_callback=self.before_agent_callback,
            before_model_callback=self.before_model_callback,
            description=(
                "This Routing agent orchestrates requests for the user "
                "to assist in live news or sports broadcast control"),
            tools=[self.send_message],
        )
        return self._agent

    def check_active_agent(self, context: ReadonlyContext):
        """Checks for an active agent session in the context."""
        state = context.state
        if ("session_id" in state and "session_active" in state
                and state["session_active"] and "active_agent" in state):
            return {"active_agent": f"{state['active_agent']}"}
        return {"active_agent": "None"}

    def _get_formatted_instructions(
            self,
            rundown_system_preference: str) -> str:
        """
        Formats the system instructions with all necessary placeholders based on
        the selected rundown system.
        """
        system_config = AUTOMATION_SYSTEMS.get(rundown_system_preference, {})
        rundown_instructions = system_config.get("instructions",
                                                 DEFAULT_INSTRUCTIONS)

        # Return the correct rundown instruction to be placed into state
        # for placeholder replacement.
        return rundown_instructions

    async def before_agent_callback(self, callback_context: CallbackContext,
                                    **kwargs):
        """A callback executed before the agent is called."""
        await self._async_init_if_needed()
        user_id = callback_context.state.get("user_id")

        logger.info("before_agent_callback called for user: %s", user_id)
        rundown_system_preference = "cuez"  # A safe default

        if user_id:
            try:
                db = firestore.AsyncClient()

                # Fetch the user's preference document
                doc_ref = db.collection('user_preferences').document(user_id)
                doc = await doc_ref.get()

                if doc.exists:
                    rundown_system_preference = doc.to_dict().get(
                        'rundown_system', 'cuez')

                logger.info("User '%s' preference set to: %s", user_id,
                            rundown_system_preference)

            except Exception as e:
                logger.error(
                    "Failed to fetch user preferences for %s: %s. Using default.",
                    user_id, e)

        # Dynamically load the preferred rundown agent
        rundown_agent_connection = None
        preferred_system_config = AUTOMATION_SYSTEMS.get(
            rundown_system_preference)
        if preferred_system_config:
            agent_configs = load_remote_agents_config()
            target_config_name = preferred_system_config['config_name']

            rundown_agent_config = next(
                (c for c in agent_configs if c['name'] == target_config_name),
                None)

            if rundown_agent_config:
                url = os.getenv(rundown_agent_config["url_env"],
                                rundown_agent_config["default_url"])
                api_key = os.getenv(rundown_agent_config["key_env"])
                rundown_agent_connection = await self._load_agent(url, api_key)
                if rundown_agent_connection:
                    callback_context.state[
                        'rundown_agent_connection'] = rundown_agent_connection
                    logger.info("Dynamically loaded rundown agent: %s",
                                rundown_agent_connection.card.name)
                else:
                    logger.error(
                        "Failed to dynamically load rundown agent for preference: %s",
                        rundown_system_preference)

        # Build the list of available agents for the prompt
        available_agents = []
        for name, conn in self.remote_agent_connections.items():
            available_agents.append(f"- `{name}`: {conn.card.description}")

        if rundown_agent_connection:
            card = rundown_agent_connection.card
            available_agents.append(f"- `{card.name}`: {card.description}")

        available_agents_list = "\n".join(available_agents)
        rundown_instructions = self._get_formatted_instructions(
            rundown_system_preference)

        # If the preferred agent failed to load, override the instructions
        # to inform the model (and user) about the problem.
        if not rundown_agent_connection and preferred_system_config:
            agent_name = preferred_system_config.get('agent_name',
                                                   rundown_system_preference)
            logger.info("INSTRUCTIONS AGENT NAME: %s", agent_name)
            rundown_instructions = (
                f"IMPORTANT: The preferred rundown system agent ('{agent_name}') "
                "failed to load. Inform the user that you cannot connect to it "
                "and that they should check the agent's status. Do not attempt to use it."
            )

        # Set the template variables in the state for the ADK to format.
        callback_context.state[
            'rundown_system_instructions'] = rundown_instructions
        callback_context.state['available_agents_list'] = available_agents_list
        callback_context.state[
            'rundown_system_preference'] = rundown_system_preference

    async def before_model_callback(self, callback_context: CallbackContext,
                                    **kwargs):
        """A callback executed before the model is called."""
        await self._async_init_if_needed()
        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    def list_remote_agents(self) -> list[dict[str, str]]:
        """List the available remote agents you can use to delegate the task."""
        if not self.cards:
            return []

        remote_agent_info = []
        for card in self.cards.values():

            # This tool is for the agent to discover available remote agents.
            logger.info("Found agent card: %s", card.name)
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
        state = tool_context.state

        rundown_agent_names = {
            config['agent_name']
            for config in AUTOMATION_SYSTEMS.values()
        }

        client = None
        # Case-insensitive check for rundown agents
        if agent_name.lower() in [name.lower() for name in rundown_agent_names]:
            rundown_connection = state.get('rundown_agent_connection')
            # Case-insensitive comparison with the card name
            if rundown_connection and rundown_connection.card.name.lower() == agent_name.lower():
                client = rundown_connection
            else:
                error_message = (
                    f"Error: Rundown agent '{agent_name}' not loaded for this session."
                )
                logger.error(error_message)
                return [error_message]
        else:
            if agent_name in self.remote_agent_connections:
                client = self.remote_agent_connections[agent_name]

        if not client:
            available_agents = list(self.remote_agent_connections.keys())
            if 'rundown_agent_connection' in state:
                available_agents.append(
                    state['rundown_agent_connection'].card.name)

            error_message = (f"Error: Agent '{agent_name}' not found. "
                             "Available agents are: "
                             f"{available_agents}")
            logger.error(error_message)
            return [error_message]

        state = tool_context.state
        state["active_agent"] = agent_name

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
        except A2AClientTimeoutError as e:
            error_message = (
                f"Request to agent '{agent_name}' timed out. The agent might be "
                "overloaded or unresponsive."
            )
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
root_agent = routing_agent_instance.get_agent()