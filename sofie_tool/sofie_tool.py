Okay, let's reformat the Sofie agent's functionality into a structure that would be more typical for an Agent Development Kit (ADK).

This usually involves:
1.  **A System Prompt:** Defining the agent's role, capabilities, goals, and how it should use its tools.
2.  **Tool Definitions:** Python functions that the agent can call. These functions will encapsulate interactions with the `SofieAPIClient` and the `MCPToolClient`. Docstrings for these tools are crucial as the ADK's LLM often uses them to understand how and when to use the tool.
3.  **An Agent Class/Configuration:** How the ADK itself would instantiate and run this agent (this part will be more conceptual as ADKs vary).

Here's the adaptation:

```python
#!/usr/bin/env python3

"""
Sofie Agent for ADK (Agent Development Kit)

This file defines the components for a Sofie Agent intended to be run
within an Agent Development Kit. It includes:
- A detailed system prompt for the LLM.
- Tool definitions (Python functions) that allow the agent to interact
  with a Sofie Playout System and an MCP (Multi-Agent Co-ordination Protocol) tool
  for communication with an Orchestrator Agent.
- Placeholder API clients for Sofie and MCP.
"""

import time
import logging
from enum import Enum
from typing import Any, Dict, Optional, List, Callable

# --- Configuration & Constants ---
# (Same as before, but some might be implicitly handled by ADK or LLM context)

class MCP_MESSAGE_TAG(Enum):
    RUNNING_ORDER_UPDATE = "RUNNING_ORDER_UPDATE"
    PLAYOUT_EVENT = "PLAYOUT_EVENT"
    STATE_CONFIRMATION = "STATE_CONFIRMATION"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    ERROR_REPORT = "ERROR_REPORT"
    # Tags for messages received FROM Orchestrator
    COMMAND = "COMMAND"
    QUERY_REQUEST = "QUERY_REQUEST"

class SOFIE_ITEM_STATUS(Enum):
    ON_AIR = "on-air"
    FINISHED = "finished"
    NEXT_UP = "next up"
    CUED = "cued"
    ERROR = "error"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SofieADKAgent")

# --- Placeholder External System Clients ---
# These would be initialized and passed to the tool functions,
# or the tools might be methods of a class that holds these clients.

class MCPToolClient:
    """Placeholder for the MCP tool client."""
    def __init__(self, client_id: str, orchestrator_agent_id: str):
        self.client_id = client_id
        self.orchestrator_agent_id = orchestrator_agent_id
        # In a real ADK, message listening might be handled by the ADK framework.
        self.incoming_message_callback: Optional[Callable[[str, MCP_MESSAGE_TAG, Dict[str, Any]], None]] = None


    def send_message(self, tag: MCP_MESSAGE_TAG, payload: Dict[str, Any]):
        """Sends a structured message to the Orchestrator Agent via MCP."""
        message_str = f"MCP SEND from {self.client_id} to {self.orchestrator_agent_id}: {tag.value}: {payload}"
        logger.info(message_str)
        # Actual network sending logic here
        return {"status": "success", "message_sent": message_str}

    def set_incoming_message_handler(self, handler: Callable[[str, MCP_MESSAGE_TAG, Dict[str, Any]], None]):
        """ADK might call this to route Orchestrator messages to the agent's logic."""
        self.incoming_message_callback = handler
        logger.info(f"MCPToolClient: Incoming message handler set for {self.client_id}")

    def _simulate_incoming_orchestrator_message(self, tag: MCP_MESSAGE_TAG, payload: Dict[str, Any]):
        """Helper for simulation to trigger the agent's processing logic."""
        if self.incoming_message_callback:
            logger.info(f"MCP SIMULATED RECV by {self.client_id} from Orchestrator: {tag.value}: {payload}")
            # In an ADK, the ADK framework would typically parse the incoming message
            # and then invoke the agent's main processing function or a specific handler.
            # The agent's system prompt would guide how it reacts to these incoming messages.
            self.incoming_message_callback(self.orchestrator_agent_id, tag, payload)
        else:
            logger.warning(f"MCP SIMULATED RECV (no handler on {self.client_id}) for Orchestrator message.")


class SofieAPIClient:
    """Placeholder for the Sofie API client."""
    def __init__(self, sofie_host: str):
        self.sofie_host = sofie_host
        self.sofie_event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._logger = logging.getLogger("SofieAPIClient")
        self._logger.info(f"Initialized for host {sofie_host}")
        self._mock_state = { # Internal mock state for simulation
            "rundown_id": "RD_INITIAL_STATE",
            "active_segment": {"name": "Startup", "id": "seg_init"},
            "active_item": {"slug": "SystemBoot", "id": "item_init", "status": SOFIE_ITEM_STATUS.ON_AIR.value},
            "next_item": {"slug": "Standby", "id": "item_stby", "status": SOFIE_ITEM_STATUS.NEXT_UP.value}
        }


    def get_current_running_order_state(self) -> Dict[str, Any]:
        self._logger.debug("Sofie API: Fetching current running order state...")
        return self._mock_state.copy()

    def set_event_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """ADK agent might register a callback to be notified of Sofie system events."""
        self.sofie_event_callback = callback
        self._logger.info("Sofie API: Event callback registered.")

    def _trigger_sofie_event(self, event_data: Dict[str, Any]):
        """Simulates Sofie system pushing an event."""
        self._logger.info(f"Sofie API Event: {event_data}")
        if self.sofie_event_callback:
            self.sofie_event_callback(event_data)

    def load_rundown(self, rundown_id: str) -> Dict[str, Any]:
        self._logger.info(f"Sofie API: Attempting to load rundown '{rundown_id}'")
        if rundown_id == "NON_EXISTENT_RUNDOWN":
            self._logger.error(f"Sofie API: Rundown '{rundown_id}' not found.")
            return {"status": "error", "message": f"Rundown '{rundown_id}' not found."}
        self._mock_state = {
            "rundown_id": rundown_id,
            "active_segment": {"name": "NewRundown_Intro", "id": "seg_new0"},
            "active_item": {"slug": "NR_Titles", "id": "item_new001", "status": SOFIE_ITEM_STATUS.CUED.value},
            "next_item": {"slug": "NR_FirstStory", "id": "item_new002", "status":