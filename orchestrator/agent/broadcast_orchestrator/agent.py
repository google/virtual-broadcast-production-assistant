"""Module for the Routing Agent."""
import json
import uuid
from typing import List
import httpx
from typing import Any
import asyncio
import os

from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from a2a.client import A2ACardResolver

from a2a.types import (
    SendMessageResponse,
    SendMessageRequest,
    MessageSendParams,
    SendMessageSuccessResponse,
    Task,
    Part,
    AgentCard,
)

from dotenv import load_dotenv

load_dotenv()


def convert_part(part: Part):
  # Currently only support text parts
  if part.type == "text":
    return part.text

  return f"Unknown type: {part.type}"


def convert_parts(parts: list[Part]):
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

  # __init__ becomes synchronous and simple
  def __init__(
      self,
      task_callback: TaskUpdateCallback | None = None,
  ):
    self.task_callback = task_callback
    self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
    self.cards: dict[str, AgentCard] = {}
    self.agents: str = ""

  # Asynchronous part of initialization
  async def _async_init_components(self, remote_agent_addresses: List[str]):
    # Use a single httpx.AsyncClient for all card resolutions for
    # efficiency
    async with httpx.AsyncClient(timeout=30) as client:
      for address in remote_agent_addresses:
        card_resolver = A2ACardResolver(client, address)
        try:
          card = await card_resolver.get_agent_card()

          remote_connection = RemoteAgentConnections(agent_card=card,
                                                     agent_url=address)
          self.remote_agent_connections[card.name] = remote_connection
          self.cards[card.name] = card
        except httpx.ConnectError as e:
          print(f"ERROR: Failed to get agent card from {address}: {e}")
        # Catch other potential errors
        except Exception as e:
          print("ERROR: Failed to initialize "
                f"connection for {address}: {e}")

    # Populate self.agents using the logic from original __init__ (via
    # list_remote_agents)
    agent_info = []
    for agent_detail_dict in self.list_remote_agents():
      agent_info.append(json.dumps(agent_detail_dict))
    self.agents = "\n".join(agent_info)

  # Class method to create and asynchronously initialize an instance
  @classmethod
  async def create(
      cls,
      remote_agent_addresses: List[str],
      task_callback: TaskUpdateCallback | None = None,
  ):
    instance = cls(task_callback)
    await instance._async_init_components(remote_agent_addresses)
    return instance

  def create_agent(self) -> Agent:
    return Agent(
        model="gemini-2.5-flash-preview-04-17",
        name="Routing_agent",
        instruction=self.root_instruction,
        before_model_callback=self.before_model_callback,
        description=(
            "This Routing agent orchestrates the decomposition of user "
            "requests for weather forecasts or Airbnb accommodations"),
        tools=[
            self.send_message,
        ],
    )

  def root_instruction(self, context: ReadonlyContext) -> str:
    current_agent = self.check_active_agent(context)
    return f"""
        **Role:** You are a multimodal live broadcast production assistant
        agent for news and sports broadcasts. Your primary goal is to assist
        the director and editor in executing a smooth and efficient live
        production. Accurately delegate user inquiries to the appropriate
        specialized remote agents.

        **Communication Style:**

        *   **CONCISE AND DIRECT LANGUAGE:** Use short, clear phrases typical
            of a live broadcast control room. Time is critical. Do not keep
            asking how else can you help. The director will ask if they need
            it.
        *   **PROMPT RESPONSES:** Respond immediately. Delays are
            unacceptable in live production.
        *   **STANDARD TERMINOLOGY:** Employ standard broadcast terms (examples
            provided below).
        *   **DO NOT MAKE ANYTHING UP** You MUST use the right tools and
            agents to get information, if you don't have any available you
            should say so. Again, do not make information up that sounds
            plausible.

        **Core Directives:**
        * **Task Delegation:** Utilize the `send_message` function to assign actionable tasks to remote agents.
        * **Contextual Awareness for Remote Agents:** If a remote agent repeatedly
          requests user confirmation, assume it lacks access to the full
          conversation history. In such cases, enrich the task description with
          all necessary contextual information relevant to that specific agent.
        * **Autonomous Agent Engagement:** Never seek user permission before
          engaging with remote agents. If multiple agents are required to fulfill
          a request, connect with them directly without requesting user
          preference or confirmation.
        * **Transparent Communication:** Always present the complete and detailed
          response from the remote agent to the user.
        * **User Confirmation Relay:** If a remote agent asks for confirmation,
          and the user has not already provided it, relay this confirmation
          request to the user.
        * **Focused Information Sharing:** Provide remote agents with only relevant
          contextual information. Avoid extraneous details.
        * **No Redundant Confirmations:** Do not ask remote agents for
          confirmation of information or actions.
        * **Tool Reliance:** Strictly rely on available tools to address user
          requests. Do not generate responses based on assumptions. If
          information is insufficient, request clarification from the user.
        * **Prioritize Recent Interaction:** Focus primarily on the most recent
          parts of the conversation when processing requests.
        * **Active Agent Prioritization:** If an active agent is already engaged,
          route subsequent related requests to that agent using the appropriate
          task update tool.

        **Agent Roster:**

        To Spellcheck, first ask cuez agents the parts and there uids from the
        rundown, then uses the spellcheck agent, if there is something to fix,
        ask the user to confirm and then ask the rundown to fix it.

        * Available Agents: `{self.agents}`
        * Currently Active Agent: `{current_agent["active_agent"]}`
                """

  def check_active_agent(self, context: ReadonlyContext):
    state = context.state
    if ("session_id" in state and "session_active" in state
        and state["session_active"] and "active_agent" in state):
      return {"active_agent": f"{state['active_agent']}"}
    return {"active_agent": "None"}

  def before_model_callback(self, callback_context: CallbackContext):
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
      print(f"Found agent card: {card.model_dump(exclude_none=True)}")
      print("=" * 100)
      remote_agent_info.append({
          "name": card.name,
          "description": card.description
      })
    return remote_agent_info

  async def send_message(self, agent_name: str, task: str,
                         tool_context: ToolContext):
    """Sends a task to remote seller agent

        This will send a message to the remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to.
            task: The comprehensive conversation context summary and goal to be
                achieved regarding user inquiry and purchase request.
            tool_context: The tool context this method runs in.

        Yields:
            A dictionary of JSON data.
        """
    if agent_name not in self.remote_agent_connections:
      raise ValueError(f"Agent {agent_name} not found")
    state = tool_context.state
    state["active_agent"] = agent_name
    client = self.remote_agent_connections[agent_name]

    if not client:
      raise ValueError(f"Client not available for {agent_name}")
    if "task_id" in state:
      task_id = state["task_id"]

    else:
      task_id = str(uuid.uuid4())
    state["task_id"] = task_id  # Ensure task_id is stored in state
    # session_id is initialized in before_model_callback
    if "context_id" in state:
      context_id = state["context_id"]
    else:
      context_id = str(uuid.uuid4())

    message_id = ""
    metadata = {}
    if "input_message_metadata" in state:
      metadata.update(**state["input_message_metadata"])
      if "message_id" in state["input_message_metadata"]:
        message_id = state["input_message_metadata"]["message_id"]
    if not message_id:
      message_id = str(uuid.uuid4())

    payload = {
        "message": {
            "role": "user",
            "parts": [{
                "type": "text",
                "text": task
            }],
            "messageId": message_id,
        },
    }

    if task_id:
      payload["message"]["taskId"] = task_id

    if context_id:
      payload["message"]["contextId"] = context_id

    message_request = SendMessageRequest(
        id=message_id, params=MessageSendParams.model_validate(payload))
    send_response: SendMessageResponse = await client.send_message(
        message_request=message_request)
    print("send_response", send_response)

    if not isinstance(send_response.root, SendMessageSuccessResponse):
      print("received non-success response. Aborting get task ")
      return

    if not isinstance(send_response.root.result, Task):
      print("received non-task response. Aborting get task ")
      return

    response = send_response
    if hasattr(response, "root"):
      content = response.root.model_dump_json(exclude_none=True)
    else:
      content = response.model_dump(mode="json", exclude_none=True)

    resp = []
    json_content = json.loads(content)
    print(json_content)
    if json_content.get("result") and json_content["result"].get("artifacts"):
      for artifact in json_content["result"]["artifacts"]:
        if artifact.get("parts"):
          resp.extend(artifact["parts"])
    return resp


def _get_initialized_routing_agent_sync():
  """Synchronously creates and initializes the RoutingAgent."""

  async def _async_main():
    cuez_agent_url = "http://localhost:8001"
    posture_stubzy_url = "http://localhost:10001"  # Shortened variable
    posture_url = "http://localhost:10002"
    routing_agent_instance = await RoutingAgent.create(remote_agent_addresses=[
        os.getenv("CUEZ_AGENT_URL", cuez_agent_url),
        os.getenv("POSTURE_STUBZY_AGENT_URL", posture_stubzy_url),
        os.getenv("POSTURE_AGENT_URL", posture_url)
    ])
    return routing_agent_instance.create_agent()

  try:
    return asyncio.run(_async_main())
  except RuntimeError as e:
    if "asyncio.run() cannot be called from a running event loop" in str(e):
      print("Warning: Could not initialize RoutingAgent with asyncio.run(): "
            f"{e}. This can happen if an event loop is "
            "already running (e.g., in Jupyter). Consider initializing "
            "RoutingAgent within an async function in your application.")
    raise


root_agent = _get_initialized_routing_agent_sync()
