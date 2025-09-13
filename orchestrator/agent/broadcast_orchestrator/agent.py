"Module for the Routing Agent."
import asyncio
from urllib.parse import urlparse
import json
import os
import logging
import re
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
    JSONRPCErrorResponse,
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

import hashlib

from .automation_system_instructions import (
    AUTOMATION_SYSTEMS,
    DEFAULT_INSTRUCTIONS,
)

import os
from google.cloud import secretmanager
from .agent_repository import get_all_agents
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from .firestore_observer import FirestoreAgentObserver
from .timeline_manager import process_tool_output_for_timeline
from .timeline_tool import get_uri_by_source_ref_id, get_uri_by_title
from .gcs_uploader import upload_base64_image_to_gcs

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


def get_secret(secret_id: str) -> str | None:
    """Retrieves a secret from Google Cloud Secret Manager."""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set.")
            return None
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error("Failed to retrieve secret '%s': %s", secret_id, e)
        return None


def normalize_name(name: str | None) -> str:
    """Normalizes an agent name for flexible, case-insensitive matching."""
    if not name:
        return ""
    return name.lower().replace(" ", "").replace("_", "")


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


def infer_mime_type(filename: str | None) -> str:
    """Infers the MIME type from a filename based on its extension."""
    if not filename:
        return "application/octet-stream"

    filename = filename.lower()
    if filename.endswith(".mp4"):
        return "video/mp4"
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        return "image/jpeg"
    if filename.endswith(".png"):
        return "image/png"
    # Add other common types as needed

    return "application/octet-stream"


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
            model="gemini-live-2.5-flash",
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

    def _get_formatted_instructions(self,
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
            config['config_name']
            for config in AUTOMATION_SYSTEMS.values()
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

            api_key = None
            if api_key_secret := agent_data.get("api_key_secret"):
                logger.info("Retrieving API key from secret: %s",
                            api_key_secret)
                api_key = get_secret(api_key_secret)

            try:
                card = AgentCard.model_validate(card_dict)
                connection = RemoteAgentConnections(agent_card=card,
                                                    agent_url=a2a_endpoint,
                                                    api_key=api_key)
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
                    rundown_system_preference = doc_dict.get(
                        'rundown_system', 'cuez')
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
                callback_context.state[
                    'rundown_agent_connection'] = rundown_conn
                callback_context.state[
                    'rundown_agent_config_name'] = config_name
                logger.info("Found preferred rundown agent: %s", config_name)
                rundown_instructions = self._get_formatted_instructions(
                    rundown_system_preference)
            else:
                agent_name = preferred_config.get('agent_name',
                                                  rundown_system_preference)
                rundown_instructions = (
                    "IMPORTANT: The preferred rundown system agent "
                    f"('{agent_name}') is configured but could not be loaded. "
                    "It might be offline or misconfigured. Inform the user you "
                    "cannot connect to it.")
                logger.error(
                    "Preferred rundown agent '%s' not found or offline.",
                    config_name)

        # 3. Build the list of available agents for the prompt
        available_agents = []
        for n, c in self.remote_agent_connections.items():
            description_lines = []
            display_name = c.card.name
            # Show the registered ID if it's different from the display name
            if n.lower() != display_name.lower():
                description_lines.append(
                    f"* `{display_name}` (ID: `{n}`): {c.card.description}")
            else:
                description_lines.append(
                    f"* `{display_name}`: {c.card.description}")

            if c.card.skills:
                description_lines.append("  Skills:")
                for skill in c.card.skills:
                    description_lines.append(
                        f"  - `{skill.id}` ({skill.name}): {skill.description}"
                    )
                    if skill.examples:
                        description_lines.append(
                            f"    Example: {skill.examples[0]}")
            available_agents.append("\n".join(description_lines))

        # 4. Update the callback context
        callback_context.state[
            'rundown_system_instructions'] = rundown_instructions
        callback_context.state['available_agents_list'] = "\n".join(
            available_agents)
        callback_context.state[
            'rundown_system_preference'] = rundown_system_preference

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

        # Create a mutable copy of kwargs to modify for downstream processors.
        final_kwargs = kwargs.copy()

        # Rehydrate the tool response for the timeline and observer.
        llm_response = kwargs.get("tool_response", [])
        part_cache = tool_context.state.get("part_cache", {})

        rehydrated_response = []
        if llm_response and isinstance(llm_response, list):
            for item_str in llm_response:
                try:
                    item = json.loads(item_str)
                    # If this is a sanitized file part, replace it with the original from the cache
                    if item.get("kind") == "file":
                        placeholder_uri = item.get("file", {}).get("uri", "")
                        if placeholder_uri.startswith("https://invalid.com/"):
                            asset_id = placeholder_uri.split("/")[-2]
                            if asset_id in part_cache:
                                # Replace the entire sanitized part with the original full part
                                rehydrated_response.append(
                                    json.dumps(part_cache[asset_id]))
                                logger.info(
                                    "Rehydrated full part for asset ID %s",
                                    asset_id)
                                continue  # Continue to next item_str

                    # If it wasn't a sanitized part that we replaced, append it as is.
                    rehydrated_response.append(item_str)
                except (json.JSONDecodeError, TypeError):
                    rehydrated_response.append(item_str)

        final_kwargs["tool_response"] = rehydrated_response

        # --- Intelligent Rundown State Caching ---
        # This logic should run on the rehydrated data.
        args = final_kwargs.get("args", {})
        agent_name = args.get("agent_name", "")
        tool_response = final_kwargs.get("tool_response")

        rundown_connection = tool_context.state.get('rundown_agent_connection')
        is_rundown_agent = False
        if rundown_connection and agent_name:
            norm_agent_name = normalize_name(agent_name)
            norm_config_name = normalize_name(
                tool_context.state.get('rundown_agent_config_name'))
            norm_card_name = normalize_name(rundown_connection.card.name)
            if norm_agent_name in (norm_config_name, norm_card_name):
                is_rundown_agent = True

        if is_rundown_agent and tool_response and isinstance(
                tool_response, list):
            try:
                new_data = json.loads(tool_response[0])
                state_data = tool_context.state.get("rundown_data", {})

                is_full = 'blocks' in new_data or 'items' in new_data
                is_single = 'id' in new_data and not is_full

                if is_full or not state_data:
                    logger.info("Storing full rundown data in session state.")
                    tool_context.state["rundown_data"] = new_data
                elif is_single:
                    item_key = 'blocks' if 'blocks' in state_data else 'items'
                    if item_key in state_data:
                        logger.info(
                            f"Merging item '{new_data['id']}' into state.")
                        found = False
                        for i, item in enumerate(state_data[item_key]):
                            if item.get('id') == new_data['id']:
                                state_data[item_key][i] = new_data
                                found = True
                                break
                        if not found:
                            state_data[item_key].append(new_data)
                    else:  # state has no item list
                        tool_context.state["rundown_data"] = new_data
            except (json.JSONDecodeError, IndexError, TypeError) as e:
                logger.warning("Could not parse/merge rundown data: %s", e)

        await self.observer.after_tool(**final_kwargs)
        await process_tool_output_for_timeline(**final_kwargs)

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
                           tool_context: ToolContext, **kwargs) -> list[str]:
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
        logger.info("RAW task from LLM for agent '%s': '%s', kwargs: %s",
                    agent_name, task, kwargs)
        state = tool_context.state
        client = None
        normalized_agent_name = normalize_name(agent_name)

        # 1. Check if the requested agent is the session's preferred rundown agent.
        preferred_config_name = state.get('rundown_agent_config_name')
        rundown_connection = state.get('rundown_agent_connection')
        canonical_id = None

        if preferred_config_name and rundown_connection:
            norm_config_name = normalize_name(preferred_config_name)
            norm_card_name = normalize_name(rundown_connection.card.name)
            if normalized_agent_name in (norm_config_name, norm_card_name):
                client = rundown_connection
                canonical_id = preferred_config_name

        # 2. If it's not the rundown agent, search the general pool of agents.
        if not client:
            matched_connections = []
            for conn_id, connection in self.remote_agent_connections.items():
                norm_conn_id = normalize_name(conn_id)
                norm_card_name = normalize_name(connection.card.name)
                if normalized_agent_name in (norm_conn_id, norm_card_name):
                    # Store the connection and its canonical ID
                    matched_connections.append((conn_id, connection))

            if len(matched_connections) == 1:
                canonical_id, client = matched_connections[0]
            elif len(matched_connections) > 1:
                # Handle ambiguity
                matched_names = [c.card.name for _, c in matched_connections]
                error_message = (
                    f"Error: The agent name '{agent_name}' is ambiguous and matches "
                    f"multiple available agents: {matched_names}. Please be more specific."
                )
                logger.error(error_message)
                return [error_message]

        # 3. If no agent was found, return an error.
        if not client:
            available_agents = [
                c.card.name for c in self.remote_agent_connections.values()
            ]
            if rundown_connection:
                available_agents.append(rundown_connection.card.name)

            error_message = (
                f"Error: Agent '{agent_name}' not found or is not online. "
                f"Available agents are: {', '.join(available_agents)}")
            logger.error(error_message)
            return [error_message]

        state["active_agent"] = client.card.name

        # 4. Use the canonical ID for creating state keys to ensure context is maintained
        agent_specific_task_id_key = f"{canonical_id}_task_id"
        task_id = state.get(agent_specific_task_id_key)

        agent_specific_context_id_key = f"{canonical_id}_context_id"
        context_id = state.get(agent_specific_context_id_key)
        if not context_id:
            context_id = str(uuid.uuid4())
            state[agent_specific_context_id_key] = context_id

        message_id = state.get("input_message_metadata",
                               {}).get("message_id", str(uuid.uuid4()))

        # 5. Construct the message payload, resolving any asset IDs to real URIs
        payload = kwargs.copy()
        payload['task'] = task
        text_content = task  # Fallback for simple text-based tasks
        message_parts: list[Part] = []
        is_structured_task = "input_uri" in payload

        source_ref_id = None
        real_uri = None
        pattern_to_replace_in_task_string = None  # Only used for string-based tasks

        # 1. Check for structured URI first
        if is_structured_task:
            placeholder_uri = payload.get("input_uri")
            if placeholder_uri and placeholder_uri.startswith(
                    "https://invalid.com/"):
                match = re.search(r'https://invalid\.com/([a-z0-9_-]+)/',
                                  placeholder_uri)
                if match:
                    source_ref_id = match.group(1)
                    logger.info("Found structured placeholder URI with ID: %s",
                                source_ref_id)

        # 2. If not found in structured payload, search the raw task string
        if not source_ref_id:
            logger.info(
                "No structured URI found, searching for patterns in task string."
            )
            placeholder_match = re.search(
                r'https://invalid\.com/([a-z0-9_-]+)/', task)
            id_match = re.search(r"id\s+([\w\-_.]+)", task, re.IGNORECASE)
            filename_match = re.search(
                r'([^\s/]+\.(?:mp4|mov|wav|jpg|jpeg|png))', task,
                re.IGNORECASE)

            if placeholder_match:
                source_ref_id = placeholder_match.group(1)
                pattern_to_replace_in_task_string = placeholder_match.group(0)
                logger.info("Found string placeholder URI with ID: %s",
                            source_ref_id)
            elif id_match:
                source_ref_id = id_match.group(1)
                pattern_to_replace_in_task_string = id_match.group(0)
                logger.info("Found raw asset ID in string: %s", source_ref_id)
            elif filename_match:
                source_ref_id = filename_match.group(1)
                pattern_to_replace_in_task_string = filename_match.group(0)
                logger.info("Found filename in string: %s", source_ref_id)

        # 3. If we have an ID, resolve it to a real URI
        if source_ref_id:
            real_uri = None
            mime_type = "application/octet-stream"  # Default

            # --- Primary Lookup: By ID ---
            if "video_assets" in tool_context.state and source_ref_id in tool_context.state[
                    "video_assets"]:
                cached_asset = tool_context.state["video_assets"][
                    source_ref_id]
                real_uri = cached_asset.get("uri")
                mime_type = cached_asset.get("mime_type", mime_type)
                logger.info("Resolved asset from state cache for ID: %s",
                            source_ref_id)

            if not real_uri:
                logger.info(
                    "URI not in cache. Calling get_uri_by_source_ref_id for ID: %s",
                    source_ref_id)
                resolved_data_str = await get_uri_by_source_ref_id(
                    source_ref_id)
                if resolved_data_str and "Error:" not in resolved_data_str:
                    try:
                        resolved_data = json.loads(resolved_data_str)
                        real_uri = resolved_data.get("uri")
                        mime_type = resolved_data.get("mime_type", mime_type)
                    except json.JSONDecodeError:
                        logger.warning("Could not decode file data for ID %s",
                                       source_ref_id)
                        real_uri = None
                else:
                    real_uri = None

            # --- Secondary Lookup: By Title ---
            if not real_uri:
                logger.warning(
                    "Could not resolve '%s' as an ID. Attempting fallback lookup by title.",
                    source_ref_id)
                video_assets_cache = tool_context.state.get("video_assets", {})
                found_by_title = False
                for asset_id, asset_details in video_assets_cache.items():
                    if asset_details.get(
                            "title") and source_ref_id in asset_details.get(
                                "title"):
                        logger.info(
                            "Fallback successful: Found match by title in cache for asset ID %s",
                            asset_id)
                        real_uri = asset_details.get("uri")
                        mime_type = asset_details.get("mime_type", mime_type)
                        found_by_title = True
                        break

                if not found_by_title:
                    logger.info(
                        "Asset not found in cache by title, checking Firestore."
                    )
                    session_id = tool_context.state.get("session_id")
                    if session_id:
                        resolved_data_str = await get_uri_by_title(
                            source_ref_id, session_id)
                        if resolved_data_str and "Error:" not in resolved_data_str:
                            try:
                                resolved_data = json.loads(resolved_data_str)
                                real_uri = resolved_data.get("video_uri")
                                mime_type = resolved_data.get(
                                    "mime_type", mime_type)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "Could not decode file data for title %s",
                                    source_ref_id)

            if not real_uri:
                logger.warning(
                    "Failed to resolve ID or Title to URI: %s. Passing original task downstream.",
                    source_ref_id)

        # 4. Construct the final message parts based on task type
        if is_structured_task:
            # We had a structured task, so update the payload and send as DataPart
            if real_uri:
                payload["input_uri"] = real_uri
                logger.info("Updated structured payload with real URI: %s",
                            payload["input_uri"])
            message_parts.append(Part(root=DataPart(data=payload)))
            logger.info(
                "Sending structured DataPart payload (URI may be unresolved).")
        else:
            # It was a simple string task. Replace the pattern in the string and send as TextPart.
            text_content = task  # Start with the original task
            if real_uri and pattern_to_replace_in_task_string:
                text_content = task.replace(pattern_to_replace_in_task_string,
                                            real_uri)
                logger.info("Updated TextPart with real URI: %s", text_content)

            if text_content:
                message_parts.append(Part(root=TextPart(text=text_content)))

            if real_uri and "cuez" not in agent_name.lower():
                asset_title = ""
                if "video_assets" in tool_context.state and source_ref_id in tool_context.state[
                        "video_assets"]:
                    asset_title = tool_context.state["video_assets"][
                        source_ref_id].get("title")
                final_mime_type = infer_mime_type(asset_title)
                file_part = Part(root=FilePart(
                    file=FileWithUri(uri=real_uri, mime_type=final_mime_type)))
                message_parts.append(file_part)
                logger.info(
                    "Adding supplementary FilePart for non-Cuez agent.")

        if not message_parts:
            return ["Error: Could not construct a message to send."]

        message_to_send = Message(
            role="user",
            parts=message_parts,
            message_id=message_id,
            task_id=task_id,
            context_id=context_id,
        )

        params = MessageSendParams(message=message_to_send)
        message_request = SendMessageRequest(id=message_id, params=params)

        try:
            logger.info("Sending A2A payload: %s",
                        message_request.model_dump_json(indent=2))

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

        if (isinstance(send_response.root, JSONRPCErrorResponse)
                and send_response.root.error and "is in terminal state"
                in (send_response.root.error.message or "")):
            logger.warning(
                "Task ID %s is in a terminal state. Clearing it and retrying.",
                task_id)
            if agent_specific_task_id_key in state:
                state[agent_specific_task_id_key] = None

            # Create a new message object for the retry, preserving the original
            retry_message_to_send = Message(
                role=message_to_send.role,
                parts=message_to_send.parts,
                message_id=message_to_send.message_id,
                task_id=None,
                context_id=message_to_send.context_id,
            )
            params = MessageSendParams(message=retry_message_to_send)
            message_request = SendMessageRequest(id=message_id, params=params)

            try:
                logger.info("Retrying A2A payload: %s",
                            message_request.model_dump_json(indent=2))
                send_response = await client.send_message(
                    message_request=message_request)
                logger.info("Retry send_response %s", send_response)
            except (httpx.ConnectError, A2AClientTimeoutError) as e:
                error_message = (
                    "Network connection failed during retry to agent "
                    f"'{agent_name}'.")
                logger.error("ERROR: %s Details: %s", error_message, e)
                return [error_message]

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            error_text = "Failed to send message."
            if (isinstance(send_response.root, JSONRPCErrorResponse)
                    and send_response.root.error):
                error_text = f"Failed to send message: {send_response.root.error.message}"
            logger.warning(
                "received non-success response. Aborting get task. %s",
                error_text)
            return [error_text]

        result = send_response.root.result

        if not isinstance(result, (Task, Message)):
            logger.warning("received unexpected response. Aborting get task ")
            return [f"Received an unexpected response type: {type(result)}"]

        response_json_string = result.model_dump_json(exclude_none=True)
        tool_context.state["last_a2a_response"] = response_json_string

        if isinstance(result, Task) and result.id:
            state[agent_specific_task_id_key] = result.id

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

        if not parts_to_process and isinstance(result, Task):
            return [result.model_dump_json(exclude_none=True)]

        for part in parts_to_process:
            part_dict = part.model_dump(exclude_none=True)

            # New logic for handling base64 images from Newsroom Agent
            agent_card_name = client.card.name.lower()
            file_details = part_dict.get("file", {})
            if 'newsroom agent' in agent_card_name and file_details.get("bytes"):
                try:
                    logger.info("Image upload logic triggered for Newsroom Agent.")
                    base64_data = file_details.get("bytes")
                    filename = file_details.get("name") or str(uuid.uuid4()) + ".png"
                    logger.info("Attempting to upload image with filename: %s", filename)
                    
                    public_url = await upload_base64_image_to_gcs(base64_data, filename)
                    
                    if public_url:
                        logger.info("Image upload successful. URL: %s", public_url)
                        del part_dict["file"]["bytes"]
                        part_dict["file"]["uri"] = public_url
                        if "mime_type" not in part_dict["file"]:
                            part_dict["file"]["mime_type"] = "image/png"
                    else:
                        logger.error("upload_base64_image_to_gcs returned None for file: %s", filename)
                except Exception as e:
                    logger.error("EXCEPTION during image upload: %s", e, exc_info=True)

            if part_dict.get("kind") == "file":
                metadata = part_dict.get("metadata", {})
                file_details = part_dict.get("file", {})
                
                asset_id = metadata.get("id") or metadata.get("moment_id")
                real_uri = file_details.get("uri")

                if asset_id and real_uri:
                    logger.info("Sanitizing URI for asset ID %s", asset_id)
                    
                    if "video_assets" not in tool_context.state:
                        tool_context.state["video_assets"] = {}
                    
                    real_mime_type = file_details.get("mime_type") or file_details.get("mimeType") or "application/octet-stream"
                    tool_context.state["video_assets"][asset_id] = {
                        "uri": real_uri,
                        "mime_type": real_mime_type,
                        "title": metadata.get("title")
                    }
                    
                    part_dict["file"]["uri"] = f"https://invalid.com/{asset_id}/"
                    
                    if "part_cache" not in tool_context.state:
                        tool_context.state["part_cache"] = {}
                    original_part = part.model_dump(exclude_none=True)
                    tool_context.state["part_cache"][asset_id] = original_part

            output_parts.append(json.dumps(part_dict))

        return output_parts
