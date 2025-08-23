"Module for the Routing Agent."
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
from a2a.client.errors import A2AClientTimeoutError, A2AClientHTTPError
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
from firebase_admin import firestore_async
from google.cloud.exceptions import GoogleCloudError
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext

from .automation_system_instructions import (
    AUTOMATION_SYSTEMS,
    DEFAULT_INSTRUCTIONS,
)

from .config import (
    load_remote_agents_config,
    load_system_instructions,
)
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from .firestore_observer import FirestoreAgentObserver

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


# pylint: disable=too-many-instance-attributes
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
        self.observer = FirestoreAgentObserver()

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
            except (httpx.ConnectError, A2AClientHTTPError) as e:
                logger.error("Failed to get agent card from %s: %s", address,
                             e)
            except IOError as e:
                logger.error("Failed to initialize connection for %s: %s",
                             address, e)

        return None

    async def _async_init_components(self,
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

        agent_info = [json.dumps(d) for d in self.list_remote_agents()]
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

            await self._async_init_components(remote_agents_config)
            self._initialized = True

    def get_agent(self) -> Agent:
        """Creates and returns the ADK Agent instance if it doesn't exist."""
        if self._agent:
            return self._agent

        initial_instructions = load_system_instructions()

        self._agent = Agent(
            model="gemini-live-2.5-flash",
            name="Routing_agent",
            instruction=initial_instructions,
            before_agent_callback=self.before_agent_callback,
            after_agent_callback=self.after_agent_callback,
            before_tool_callback=self.observer.before_tool,
            after_tool_callback=self.observer.after_tool,
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

    def _get_formatted_instructions(self,
                                    rundown_system_preference: str) -> str:
        """
        Formats the system instructions based on the selected rundown system.
        """
        system_config = AUTOMATION_SYSTEMS.get(rundown_system_preference, {})
        return system_config.get("instructions", DEFAULT_INSTRUCTIONS)

    # pylint: disable=too-many-locals
    async def before_agent_callback(self, callback_context: CallbackContext):
        """A callback executed before the agent is called."""
        print("!!! AGENT.PY: before_agent_callback IS RUNNING !!!")

        await self._async_init_if_needed()
        user_id = callback_context.state.get("user_id")

        logger.info("before_agent_callback called for user: %s", user_id)
        rundown_system_preference = "cuez"  # A safe default

        if user_id:
            try:
                db = firestore_async.client()
                doc_ref = db.collection('user_preferences').document(user_id)
                doc = await doc_ref.get()
                if doc.exists:
                    rundown_system_preference = doc.to_dict().get(
                        'rundown_system', 'cuez')
                logger.info("User '%s' preference set to: %s", user_id,
                            rundown_system_preference)
            except GoogleCloudError as e:
                logger.error(
                    "Failed to fetch user preferences for %s: %s. Using default.",
                    user_id, e)

        preferred_config = AUTOMATION_SYSTEMS.get(rundown_system_preference)
        rundown_conn = None
        if preferred_config:
            agent_configs = load_remote_agents_config()
            config_name = preferred_config['config_name']
            agent_config = next(
                (c for c in agent_configs if c['name'] == config_name), None)

            if agent_config:
                url = os.getenv(agent_config["url_env"],
                                agent_config["default_url"])
                api_key = os.getenv(agent_config["key_env"])
                rundown_conn = await self._load_agent(url, api_key)
                if rundown_conn:
                    callback_context.state[
                        'rundown_agent_connection'] = rundown_conn
                    logger.info("Dynamically loaded rundown agent: %s",
                                rundown_conn.card.name)
                else:
                    logger.error(
                        "Failed to dynamically load rundown agent for preference: %s",
                        rundown_system_preference)

        available_agents = [
            f"- `{n}`: {c.card.description}"
            for n, c in self.remote_agent_connections.items()
        ]
        if rundown_conn:
            available_agents.append(
                f"- `{rundown_conn.card.name}`: {rundown_conn.card.description}"
            )

        rundown_instructions = self._get_formatted_instructions(
            rundown_system_preference)
        if not rundown_conn and preferred_config:
            agent_name = preferred_config.get('agent_name',
                                              rundown_system_preference)
            rundown_instructions = (
                "IMPORTANT: The preferred rundown system agent "
                f"('{agent_name}') failed to load. Inform the user that you "
                "cannot connect to it and that they should check the agent's "
                "status. Do not attempt to use it.")

        callback_context.state[
            'rundown_system_instructions'] = rundown_instructions
        callback_context.state['available_agents_list'] = "\n".join(
            available_agents)
        callback_context.state[
            'rundown_system_preference'] = rundown_system_preference

    async def after_agent_callback(self, callback_context: CallbackContext):
        """A callback executed after the agent has finished."""
        logger.info("after_agent_callback called")

    async def before_model_callback(self, callback_context: CallbackContext):
        """A callback executed before the model is called."""
        logger.info("before_model_callback called")
        await self._async_init_if_needed()
        await self.observer.before_model(context=callback_context)
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
            logger.info("Found agent card: %s", card.name)
            logger.info("=%s", "=" * 100)
            remote_agent_info.append({
                "name": card.name,
                "description": card.description
            })
        return remote_agent_info

    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements,too-many-locals
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
        logger.info("Sending task to %s: %s", agent_name, task)
        state = tool_context.state

        rundown_agent_names = {
            config['agent_name']
            for config in AUTOMATION_SYSTEMS.values()
        }

        client = None
        if agent_name.lower() in [
                name.lower() for name in rundown_agent_names
        ]:
            rundown_connection = state.get('rundown_agent_connection')
            if rundown_connection and rundown_connection.card.name.lower(
            ) == agent_name.lower():
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
                             f"Available agents are: {available_agents}")
            logger.error(error_message)
            return [error_message]

        state["active_agent"] = agent_name

        task_id = state.get("task_id", str(uuid.uuid4()))
        state["task_id"] = task_id
        context_id = state.get("context_id", str(uuid.uuid4()))
        state["context_id"] = context_id
        message_id = state.get("input_message_metadata",
                               {}).get("message_id", str(uuid.uuid4()))

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
                "overloaded or unresponsive.")
            logger.error("ERROR: %s Details: %s", error_message, e)
            return [error_message]
        logger.info("send_response %s", send_response)

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            logger.warning("received non-success response. Aborting get task ")
            return ["Failed to send message."]

        result = send_response.root.result

        if not isinstance(result, (Task, Message)):
            logger.warning("received unexpected response. Aborting get task ")
            return [f"Received an unexpected response type: {type(result)}"]

        content = result.model_dump_json(exclude_none=True)
        json_content = json.loads(content)

        resp = []
        if json_content.get("artifacts"):
            for artifact in json_content["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(
                        convert_parts([
                            Part.model_validate(p) for p in artifact["parts"]
                        ]))
        elif json_content.get("parts"):
            resp.extend(
                convert_parts(
                    [Part.model_validate(p) for p in json_content["parts"]]))
        return resp
