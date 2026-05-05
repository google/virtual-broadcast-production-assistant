"""ADK callbacks for observing and logging agent events to Firestore."""

import logging
import os
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from firebase_admin import firestore_async
from firebase_admin.firestore import SERVER_TIMESTAMP

logger = logging.getLogger(__name__)


class FirestoreAgentObserver:
    """An observer that logs agent lifecycle events to Firestore."""

    def __init__(self):
        """Initializes the Firestore async client."""
        self.db = firestore_async.client()

    def _get_event_collection(
        self, context: CallbackContext
    ) -> firestore_async.AsyncCollectionReference:
        """Gets a reference to the events collection for a given session."""
        session_id = context.state.get("session_id")
        if not session_id:
            raise ValueError("session_id not found in agent context state.")
        return self.db.collection("chat_sessions").document(session_id).collection(
            "events")

    async def user_message(self, context: CallbackContext, **kwargs):
        """Logs the User message AGENT TO CLIENT."""
        event_data = {
            "type": "USER_MESSAGE",
            "timestamp": SERVER_TIMESTAMP,
            "prompt": context.model.prompt,
        }
        await self._get_event_collection(context).add(event_data)

    async def model_message(self, context: CallbackContext, **kwargs):
        """Logs the User message AGENT TO CLIENT."""
        event_data = {
            "type": "AGENT_MESSAGE",
            "timestamp": SERVER_TIMESTAMP,
            "prompt": context.model.prompt,
        }
        await self._get_event_collection(context).add(event_data)

    async def before_model(self, context: CallbackContext, **kwargs):
        """Logs the prompt before calling the LLM."""
        event_data = {
            "type": "MODEL_START",
            "timestamp": SERVER_TIMESTAMP,
            "prompt": context.model.prompt,
        }
        await self._get_event_collection(context).add(event_data)

    async def after_model(self, context: CallbackContext, **kwargs):
        """Logs the response after receiving it from the LLM."""
        event_data = {
            "type": "MODEL_END",
            "timestamp": SERVER_TIMESTAMP,
            "response": context.model.response,
        }
        await self._get_event_collection(context).add(event_data)

    async def before_tool(self, **kwargs):
        """Logs the tool and its arguments before execution."""
        context = kwargs.get("tool_context")
        tool = kwargs.get("tool")
        if not context or not tool:
            logger.warning("Could not log before_tool event: context or tool missing.")
            return

        event_data = {
            "type": "TOOL_START",
            "timestamp": SERVER_TIMESTAMP,
            "tool_name": tool.name,
            "tool_args": kwargs.get("args"),
        }
        await self._get_event_collection(context).add(event_data)

    async def after_tool(self, **kwargs):
        """Logs the tool's output after execution."""
        context = kwargs.get("tool_context")
        tool = kwargs.get("tool")
        if not context or not tool:
            logger.warning("Could not log after_tool event: context or tool missing.")
            return

        event_data = {
            "type": "TOOL_END",
            "timestamp": SERVER_TIMESTAMP,
            "tool_name": tool.name,
            "tool_output": kwargs.get("tool_response"),
        }
        await self._get_event_collection(context).add(event_data)
