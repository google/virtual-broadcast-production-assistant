import os
import re
import json
import pathlib
from typing import Dict, List, Tuple

from fastapi import FastAPI
from pythonosc.udp_client import SimpleUDPClient

from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentInterface,
    AgentCapabilities,
    AgentSkill,
)
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.utils.message import new_agent_text_message


# --------------------------------------------------------------------------------------
# Schema loading
# --------------------------------------------------------------------------------------
SCHEMA_PATH = pathlib.Path(__file__).with_name("cuepilot_osc_schema.json")
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    CP_SCHEMA = json.load(f)

# quick lookup by id
CP_BY_ID: Dict[str, Dict] = {c["id"]: c for c in CP_SCHEMA["commands"]}


# --------------------------------------------------------------------------------------
# OSC defaults (can be overridden per-request via message.metadata)
# --------------------------------------------------------------------------------------
OSC_HOST_DEFAULT = os.getenv("OSC_HOST", "127.0.0.1")
OSC_PORT_DEFAULT = int(os.getenv("OSC_PORT", "9090"))


# --------------------------------------------------------------------------------------
# Simple intent → command picker
# --------------------------------------------------------------------------------------
SIMPLE_MAP = {
    "hold on": "holdon",
    "hold off": "holdoff",
    "load prev item": "loadprevitem",
    "load prev": "loadprevitem",
    "previous act": "loadprevitem",
    "load next item": "loadnextitem",
    "load next": "loadnextitem",
    "next act": "loadnextitem",
    "sync ltc 1": "syncltc1",
    "sync ltc1": "syncltc1",
    "sync ltc 2": "syncltc2",
    "sync ltc2": "syncltc2",
    "sync step": "syncstep",
    "sync off": "syncoff",
    "play": "play",
    "pause": "pause",
    "take": "take",
    "skip": "skip",
    "hold": "hold",
    "home": "home",
}

def _hhmmss_to_ms(val: str) -> int:
    parts = [int(x) for x in val.split(":")]
    if len(parts) == 2:
        mm, ss = parts
        return (mm * 60 + ss) * 1000
    if len(parts) == 3:
        hh, mm, ss = parts
        return (hh * 3600 + mm * 60 + ss) * 1000
    return 0

def pick_command(user_text: str) -> Tuple[str, str, List]:
    """
    Returns: (command_id, osc_address, args)
    - supports:
        - set speed <float>
        - jump to <hh:mm:ss> | <mm:ss> | <Ns>
        - keyword matches (play/pause/take/hold/etc.)
    """
    t = (user_text or "").lower().strip()

    # setspeed
    m = re.search(r"(set\s*)?speed\s*([0-9]*\.?[0-9]+)", t)
    if m:
        speed = float(m.group(2))
        cmd = CP_BY_ID["setspeed"]
        return cmd["id"], cmd["address"], [speed]

    # jumpto
    m = re.search(r"(jump\s*to|jumpto)\s*([0-9]{1,2}:[0-9]{2}:[0-9]{2}|[0-9]{1,2}:[0-9]{2}|[0-9]+s)", t)
    if m:
        val = m.group(2)
        if val.endswith("s"):
            ms = int(float(val[:-1]) * 1000.0)
        elif ":" in val:
            ms = _hhmmss_to_ms(val)
        else:
            ms = 0
        cmd = CP_BY_ID["jumpto"]
        # schema: position (string ms), do (int), speed (float)
        return cmd["id"], cmd["address"], [str(ms), 0, 0.0]

    # keywords (longest first)
    for k in sorted(SIMPLE_MAP.keys(), key=len, reverse=True):
        if k in t:
            cid = SIMPLE_MAP[k]
            cmd = CP_BY_ID[cid]
            return cmd["id"], cmd["address"], []

    # default → play
    cmd = CP_BY_ID["play"]
    return cmd["id"], cmd["address"], []


# --------------------------------------------------------------------------------------
# Executor
# --------------------------------------------------------------------------------------
class CuePilotAgentExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue):
        updater = TaskUpdater(event_queue, context.task_id or "", context.context_id or "")
        await updater.cancel(new_agent_text_message("Canceled"))

    async def execute(self, context: RequestContext, event_queue):
        updater = TaskUpdater(event_queue, context.task_id or "", context.context_id or "")
        await updater.start_work()

        # user text
        text = (context.get_user_input() or "").strip()

        # pick command
        cmd_id, address, args = pick_command(text)

        # dynamic host/port from metadata (fallback to defaults)
        meta = getattr(context, "metadata", {}) or {}
        host = meta.get("osc_host", OSC_HOST_DEFAULT)
        try:
            port = int(meta.get("osc_port", OSC_PORT_DEFAULT))
        except Exception:
            port = OSC_PORT_DEFAULT

        try:
            client = SimpleUDPClient(host, port)
            client.send_message(address, args)
            await updater.complete(
                new_agent_text_message(
                    f"Sent OSC: {address} {args} -> {host}:{port} (cmd={cmd_id})"
                )
            )
        except Exception as e:
            await updater.failed(new_agent_text_message(f"OSC error: {e}"))


# --------------------------------------------------------------------------------------
# Agent card
# --------------------------------------------------------------------------------------
def build_agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="CuePilot OSC Agent",
        version="0.2.0",
        description="Selects exactly one CuePilot OSC command and sends it over UDP/OSC.",
        url=base_url,
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        provider=AgentProvider(organization="DemoOrg", url=base_url),
        capabilities=AgentCapabilities(streaming=False),
        interfaces=[AgentInterface(transport="rest", url=base_url)],
        skills=[
            AgentSkill(
                id="cuepilot.send",
                name="Send CuePilot OSC",
                description="Map a text instruction to a single CuePilot OSC command and send it.",
                input_modes=["text"],
                output_modes=["text"],
                tags=["osc", "cuepilot"],
                examples=[
                    "play in CuePilot",
                    "pause CuePilot",
                    "take next in CuePilot",
                    "hold on",
                    "hold off",
                    "set speed 1.25",
                    "jump to 00:01:23",
                    "sync ltc1",
                    "load next item"
                ],
            )
        ],
    )


# --------------------------------------------------------------------------------------
# FastAPI app via A2A SDK
# --------------------------------------------------------------------------------------
BASE_URL = "http://localhost:9999"
agent_card = build_agent_card(BASE_URL)
executor = CuePilotAgentExecutor()

queue_manager = InMemoryQueueManager()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(executor, task_store, queue_manager)

# Use SDK defaults:
# - Agent card:            /.well-known/agent-card.json
# - Send message:          /v1/message:send
# - Task status/polling:   /v1/tasks/{id}
app: FastAPI = A2ARESTFastAPIApplication(agent_card, request_handler).build()
