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
    DataPart,
    FilePart,
    FileWithBytes,
    FileWithUri,
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
from google.genai.types import Content

from .automation_system_instructions import (
    AUTOMATION_SYSTEMS,
    DEFAULT_INSTRUCTIONS,
)

import os
from .agent_repository import get_all_agents
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from .firestore_observer import FirestoreAgentObserver
from .timeline_manager import process_tool_output_for_timeline

load_dotenv()

logger = logging.getLogger(__name__)


def load_system_instructions() -> str:
    """Loads the system instructions from a text file using an absolute path."""
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to the file
    file_path = os.path.join(script_dir, "system_instructions.txt")

    # Open the file using the absolute path
    with open(file_path, "r", encoding="utf-8") as f:
        system_instructions = f.read()

    return system_instructions


def convert_part(part: Part):
    """Converts an A2A Part to a string."""
    if isinstance(part.root, TextPart):
        return part.root.text
    if isinstance(part.root, FilePart):
        file_details = part.root.file
        if isinstance(file_details, FileWithUri):
            return {
                "type": "file",
                "uri": file_details.uri,
                "filename": file_details.name,
                "mime_type": file_details.mime_type,
            }
        if isinstance(file_details, FileWithBytes):
            return {
                "type": "file",
                "data": file_details.bytes,
                "filename": file_details.name,
                "mime_type": file_details.mime_type,
            }
    if isinstance(part.root, DataPart):
        return {"type": "data", "data": part.root.data}
    return f"Unknown type: {type(part.root)}"


def convert_parts(parts: list[Part]):
    """Converts a list of A2A Parts to a list of strings or dicts."""
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
        self.all_rundown_agents: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent: Agent | None = None
        self.observer = FirestoreAgentObserver()

    def get_agent(self) -> Agent:
        """Creates and returns the ADK Agent instance if it doesn't exist."""
        if self._agent:
            return self._agent

        initial_instructions = load_system_instructions()

        self._agent = Agent(
            model="gemini-live-2.5-flash-preview",
            name="Routing_agent",
            instruction=initial_instructions,
            before_agent_callback=self.before_agent_callback,
            after_agent_callback=self.after_agent_callback,
            before_tool_callback=self.observer.before_tool,
            after_tool_callback=self.after_tool,
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
        Formats the system instructions based on the selected rundown system.
        """
        system_config = AUTOMATION_SYSTEMS.get(rundown_system_preference, {})
        return system_config.get("instructions", DEFAULT_INSTRUCTIONS)

    async def _load_agents_from_firestore(self):
        """Loads agent configurations from Firestore and sets up connections."""
        self.remote_agent_connections = {}
        self.all_rundown_agents = {}
        self.cards = {}
        all_agents_data = await get_all_agents()

        rundown_agent_ids = {
            config['config_name'] for config in AUTOMATION_SYSTEMS.values()
        }

        for agent_data in all_agents_data:
            agent_id = agent_data.get("id")
            status = agent_data.get("status")
            card_dict = agent_data.get("card")
            a2a_endpoint = agent_data.get("a2a_endpoint")

            if status != "online" or not card_dict or not a2a_endpoint:
                logger.warning(
                    "Skipping agent '%s' due to status '%s' or missing card/endpoint.",
                    agent_id, status)
                continue

            try:
                card = AgentCard.model_validate(card_dict)
                connection = RemoteAgentConnections(
                    agent_card=card,
                    agent_url=a2a_endpoint,
                    api_key=None  # API key logic might need adjustment if required
                )
                if agent_id in rundown_agent_ids:
                    self.all_rundown_agents[agent_id] = connection
                else:
                    self.remote_agent_connections[agent_id] = connection

                self.cards[agent_id] = card
                logger.info("Successfully loaded agent: %s", agent_id)
            except Exception as e:
                logger.error("Failed to load agent '%s': %s", agent_id, e)

    # pylint: disable=too-many-locals
    async def before_agent_callback(self, callback_context: CallbackContext):
        """A callback executed before the agent is called."""
        print("!!! AGENT.PY: before_agent_callback IS RUNNING !!!")
        await self._load_agents_from_firestore()

        user_id = callback_context.state.get("user_id")
        logger.info("before_agent_callback called for user: %s", user_id)

        # 1. Determine the user's preferred rundown system
        rundown_system_preference = "cuez"  # A safe default
        if user_id:
            try:
                db = firestore_async.client()
                doc_ref = db.collection('user_preferences').document(user_id)
                doc = await doc_ref.get()
                if doc.exists:
                    doc_dict = doc.to_dict()
                    rundown_system_preference = doc_dict.get('rundown_system', 'cuez')
                logger.info("User '%s' preference set to: %s", user_id,
                            rundown_system_preference)
            except GoogleCloudError as e:
                logger.error(
                    "Failed to fetch user preferences for %s: %s. Using default.",
                    user_id, e)

        # 2. Find the rundown agent and set up its connection
        preferred_config = AUTOMATION_SYSTEMS.get(rundown_system_preference)
        rundown_conn = None
        rundown_instructions = ""

        if preferred_config:
            config_name = preferred_config.get('config_name')
            rundown_conn = self.all_rundown_agents.get(config_name)

            if rundown_conn:
                callback_context.state['rundown_agent_connection'] = rundown_conn
                callback_context.state['rundown_agent_config_name'] = config_name
                logger.info("Found preferred rundown agent: %s", config_name)
                rundown_instructions = self._get_formatted_instructions(
                    rundown_system_preference)
            else:
                agent_name = preferred_config.get('agent_name', rundown_system_preference)
                rundown_instructions = (
                    "IMPORTANT: The preferred rundown system agent "
                    f"('{agent_name}') is configured but could not be loaded. "
                    "It might be offline or misconfigured. Inform the user you "
                    "cannot connect to it.")
                logger.error("Preferred rundown agent '%s' not found or offline.", config_name)

        # 3. Build the list of available agents for the prompt
        available_agents = []
        for n, c in self.remote_agent_connections.items():
            description_lines = [f"* `{n}`: {c.card.description}"]
            if c.card.skills:
                description_lines.append("  Skills:")
                for skill in c.card.skills:
                    description_lines.append(
                        f"  - `{skill.id}` ({skill.name}): {skill.description}")
                    if skill.examples:
                        description_lines.append(
                            f"    Example: {skill.examples[0]}")
            available_agents.append("\n".join(description_lines))

        # 4. Update the callback context
        callback_context.state['rundown_system_instructions'] = rundown_instructions
        callback_context.state['available_agents_list'] = "\n".join(available_agents)
        callback_context.state['rundown_system_preference'] = rundown_system_preference

    async def after_agent_callback(self, callback_context: CallbackContext):
        """A callback executed after the agent has finished."""
        logger.info("after_agent_callback called")

    async def after_tool(self, **kwargs):
        """A callback executed after a tool has finished."""
        tool_context = kwargs.get("tool_context")
        if not tool_context:
            logger.warning(
                "Could not process after_tool event: tool_context missing.")
            return

        # Await the primary Firestore observer
        await self.observer.after_tool(**kwargs)

        # Create a background task for the timeline processing
        # so it doesn't block the agent's response to the user.
        asyncio.create_task(process_tool_output_for_timeline(**kwargs))

    async def before_model_callback(self, callback_context: CallbackContext):
        """A callback executed before the model is called."""
        logger.info("before_model_callback called")
        await self.observer.before_model(context=callback_context)
        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements,too-many-locals
    async def send_message(self, agent_name: str, task: str,
                           tool_context: ToolContext) -> list[str]:
        """Sends a task to remote seller agent

        This will send a message to the remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to.
            task: The comprehensive conversation context summary and goal to be
                achieved regarding user inquiry and purchase request. This can be
                a simple string for a text message, or a JSON string for
                complex data like a file.
            tool_context: The tool context this method runs in.

        Returns:
            A list of strings from the remote agent's response. Complex objects
            are returned as JSON strings.
        """
        logger.info("Sending task to %s: %s", agent_name, task)
        state = tool_context.state

        # Determine if the target agent is the preferred rundown agent for this session
        is_rundown_agent = False
        preferred_config_name = state.get('rundown_agent_config_name')
        if preferred_config_name and agent_name.lower() == preferred_config_name.lower():
            is_rundown_agent = True

        client = None
        if is_rundown_agent:
            client = state.get('rundown_agent_connection')
            if not client:
                error_message = (
                    f"Error: Preferred rundown agent '{agent_name}' is not available for this session."
                )
                logger.error(error_message)
                return [error_message]
        else:
            # Look for the agent in the general pool of loaded agents
            client = self.remote_agent_connections.get(agent_name)

        if not client:
            available_agents = list(self.remote_agent_connections.keys())
            error_message = (f"Error: Agent '{agent_name}' not found or is not online. "
                             f"Available agents are: {available_agents}")
            logger.error(error_message)
            return [error_message]

        state["active_agent"] = agent_name

        agent_specific_task_id_key = f"{agent_name}_task_id"
        task_id = state.get(agent_specific_task_id_key)

        agent_specific_context_id_key = f"{agent_name}_context_id"
        context_id = state.get(agent_specific_context_id_key)
        if not context_id:
            context_id = str(uuid.uuid4())
            state[agent_specific_context_id_key] = context_id

        message_id = state.get("input_message_metadata",
                               {}).get("message_id", str(uuid.uuid4()))

        payload_parts = []
        try:
            task_data = json.loads(task)
            if isinstance(task_data, dict) and 'file' in task_data:
                file_info = task_data['file']
                payload_parts.append({
                    "type": "file",
                    "file": {
                        "uri": file_info['uri'],
                        "name": file_info.get('filename', ''),
                        "mime_type": file_info['mime_type']
                    }
                })
            else:
                payload_parts.append({'type': 'text', 'text': task})
        except json.JSONDecodeError:
            payload_parts.append({'type': 'text', 'text': task})

        payload = {
            "message": {
                "role": "user",
                "parts": payload_parts,
                "messageId": message_id,
            },
        }
        if task_id:
            payload["message"]["taskId"] = task_id
        if context_id:
            payload["message"]["contextId"] = context_id

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

        # Store the full response in the context for the after_tool hook to process.
        response_json_string = result.model_dump_json(exclude_none=True)
        tool_context.state["last_a2a_response"] = response_json_string

        if isinstance(result, Task) and result.id:
            state[agent_specific_task_id_key] = result.id

        # Create and return a representation of all parts for the LLM.
        output_parts = []
        parts_to_process = []

        if isinstance(result, Message):
            parts_to_process = result.parts or []
            logger.info("Message %s", result)
        elif isinstance(result, Task):
            logger.info("Task %s", result)
            if hasattr(result, 'artifacts') and result.artifacts:
                for artifact in result.artifacts:
                    parts_to_process.extend(artifact.parts or [])

        for part in parts_to_process:
            part_dict = part.model_dump(exclude_none=True)
            output_parts.append(json.dumps(part_dict))

        return output_parts
