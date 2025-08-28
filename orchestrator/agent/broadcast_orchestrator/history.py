"""
Module for loading chat history from Firestore.
"""
import logging
from datetime import datetime, timedelta, timezone
from firebase_admin import firestore_async
from google.api_core.exceptions import PreconditionFailed
from google.cloud.exceptions import GoogleCloudError
from google.cloud.firestore_v1.base_query import FieldFilter
from google.genai.types import Content, Part as AdkPart
from google.adk.events import Event

logger = logging.getLogger(__name__)


def _convert_firestore_event_to_adk_event(event_data: dict,
                                            agent_name: str) -> Event | None:
    """Converts a Firestore event document to an ADK Event object."""
    event_type = event_data.get("type")

    if not event_type:
        logger.warning("Skipping event with no type: %s", event_data)
        return None

    author = None
    content = None

    if event_type == "USER_MESSAGE":
        author = "user"
        text = event_data.get("text") or event_data.get("prompt")
        if text:
            content = Content(parts=[AdkPart(text=text)])
    elif event_type == "AGENT_MESSAGE":
        author = agent_name
        text = (
            event_data.get("text")
            or event_data.get("prompt")
            or event_data.get("response")
        )
        if text:
            content = Content(parts=[AdkPart(text=text)])
    elif event_type == "TOOL_START":
        author = agent_name
        tool_name = event_data.get("tool_name")
        tool_args = event_data.get("tool_args", {})
        if tool_name:
            content = Content(
                parts=[AdkPart(function_call={"name": tool_name, "args": tool_args})]
            )
    elif event_type == "TOOL_END":
        author = "tool"
        tool_name = event_data.get("tool_name")
        tool_output = event_data.get("tool_output")
        if tool_name:
            response_data = tool_output
            if not isinstance(response_data, dict):
                response_data = {"output": response_data}
            content = Content(
                role="user",
                parts=[
                    AdkPart(
                        function_response={
                            "name": tool_name,
                            "response": response_data,
                        }
                    )
                ],
            )
    else:
        # Ignore other event types like MODEL_START, MODEL_END as they are for logging.
        return None

    if author and content:
        return Event(author=author, content=content)

    logger.warning("Could not convert event: %s", event_data)
    return None


async def load_chat_history(user_id: str, agent_name: str) -> list[Event]:
    """
    Loads chat history for a given user from Firestore from the last 60 minutes.
    """
    logger.info("Loading chat history for user: %s", user_id)
    if not user_id:
        return []
    try:
        db = firestore_async.client()

        # Calculate the timestamp for 60 minutes ago
        sixty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=60)

        events_ref = (
            db.collection("chat_sessions")
            .document(user_id)
            .collection("events")
            .where(filter=FieldFilter("timestamp", ">=", sixty_minutes_ago))
            .order_by("timestamp")
        )
        event_docs = events_ref.stream()
        history = []
        async for doc in event_docs:
            event_data = doc.to_dict()
            adk_event = _convert_firestore_event_to_adk_event(
                event_data, agent_name)
            if adk_event:
                history.append(adk_event)
        logger.info("Loaded %d events from chat history for user %s",
                    len(history), user_id)
        return history

    except PreconditionFailed as e:
        logger.error(
            "Failed to load chat history for user %s due to a missing Firestore index. "
            "Please create the required index. Original error: %s",
            user_id,
            e,
        )
        return []
    except GoogleCloudError as e:
        logger.error("Failed to load chat history for user %s: %s", user_id, e)
        return []
