"""
Main FastAPI application for the Broadcast Orchestrator Agent.

Handles WebSocket connections, user authentication, and orchestrates agent
sessions using the ADK.
"""
import asyncio
import base64
from contextlib import asynccontextmanager
import json
import logging
import os
# import uuid
import warnings

import firebase_admin
import yaml
from broadcast_orchestrator.agent import RoutingAgent
from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from firebase_admin import auth, firestore, firestore_async
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai.types import Blob, Content, Part

from broadcast_orchestrator.history import load_chat_history

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Load Gemini API Key
load_dotenv()


def seed_agent_status():
    """
    Reads agent configuration from a YAML file and seeds it into Firestore.

    This function is intended to be called on application startup.
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__),
                                   'remote_agents_config.yaml')
        with open(config_path, 'r', encoding="utf-8") as file:
            config = yaml.safe_load(file)
        logger.info(config)
        db = firestore.client()
        agents_ref = db.collection('agent_status')

        for agent_details in config:
            agent_id = agent_details.get('name')
            if not agent_id:
                continue

            doc_ref = agents_ref.document(agent_id)

            doc = doc_ref.get()
            if doc.exists:
                logger.info("Agent '%s' already exists in Firestore.",
                            agent_id)
                continue

            doc_data = {
                'name':
                agent_details.get('name'),
                'url':
                os.getenv(agent_details.get('url_env'),
                          agent_details.get('default_url')),
                'status':
                'offline',  # Default status
                # pylint: disable=no-member
                'last_checked':
                firestore.SERVER_TIMESTAMP
            }
            if 'secret_id' in agent_details:
                doc_data['api_key_secret'] = agent_details['secret_id']

            doc_ref.set(doc_data, merge=True)
            logger.info("Seeded/updated agent '%s' in Firestore.", agent_id)

    except (FileNotFoundError, IOError) as e:
        logger.error("Failed to read remote_agents_config.yaml: %s", e)
    except yaml.YAMLError as e:
        logger.error("Error parsing YAML file: %s", e)


#
# FastAPI web app
#
@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """
    Initializes resources on application startup.
    """
    # Initialize Firebase Admin SDK
    try:
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully.")

    except ValueError:
        logger.info("Firebase Admin SDK already initialized.")
    seed_agent_status()
    # Create and store the agent instance in the app state
    fastapi_app.state.routing_agent = RoutingAgent()

    yield

    # Anything afer yield will operate before shut down.


app = FastAPI(lifespan=lifespan)

APP_NAME = "Virtual Production Assistant"


async def start_agent_session(user_id: str,
                              app_instance: FastAPI,
                              is_audio=False):
    """Starts an agent session and returns the session ID."""

    routing_agent = app_instance.state.routing_agent
    agent = routing_agent.get_agent()
    runner = InMemoryRunner(
        app_name=APP_NAME,
        agent=agent,
    )

    history = await load_chat_history(user_id, agent.name)

    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state={
            "user_id": user_id,
            "session_id": user_id
        })

    if history:
        logger.info("Injecting %d events into session %s", len(history), session.id)
        session.events.extend(history)

    modality = "AUDIO" if is_audio else "TEXT"
    run_config = RunConfig(response_modalities=[modality])

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        user_id=user_id,
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue, user_id


async def agent_to_client_messaging(websocket: WebSocket, live_events,
                                    session_id: str,
                                    user_has_spoken: asyncio.Event):
    """Agent to client communication and agent response logging."""
    full_response = ""
    db = firestore_async.client()
    try:
        async for event in live_events:
            if not user_has_spoken.is_set():
                logger.info(
                    "[AGENT TO CLIENT]: Suppressed message because user has not spoken yet."
                )
                continue

            if event.turn_complete or event.interrupted:
                if full_response:
                    event_data = {
                        "type": "AGENT_MESSAGE",
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "text": full_response,
                    }
                    await (db.collection("chat_sessions").document(
                        session_id).collection("events").add(event_data))
                    full_response = ""

                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                logger.info("[AGENT TO CLIENT]: %s", message)
                continue

            part: Part = (event.content and event.content.parts
                          and event.content.parts[0])
            if not part:
                continue

            is_audio = part.inline_data and part.inline_data.mime_type.startswith(
                "audio/pcm")
            if is_audio:
                # Audio is not logged as part of the chat history for now.
                audio_data = part.inline_data and part.inline_data.data
                if audio_data:
                    message = {
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(audio_data).decode("ascii")
                    }
                    await websocket.send_text(json.dumps(message))
                    logger.info("[AGENT TO CLIENT]: audio/pcm: %d bytes.",
                                len(audio_data))
                    continue

            if part.text and event.partial:
                full_response += part.text
                message = {"mime_type": "text/plain", "data": part.text}
                await websocket.send_text(json.dumps(message))
                logger.info("[AGENT TO CLIENT]: text/plain: %s", message)

    except WebSocketDisconnect:
        logger.info("Client disconnected, closing agent->client messaging.")


async def client_to_agent_messaging(websocket: WebSocket, live_request_queue,
                                    session_id: str,
                                    user_has_spoken: asyncio.Event):
    """Client to agent communication and user message logging."""
    db = firestore_async.client()
    try:
        while True:
            message_json = await websocket.receive_text()
            user_has_spoken.set()
            message = json.loads(message_json)
            mime_type = message["mime_type"]
            data = message["data"]

            if mime_type == "text/plain":
                # Log the user's message to Firestore.
                event_data = {
                    "type": "USER_MESSAGE",
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "text": data,
                }
                await (db.collection("chat_sessions").document(
                    session_id).collection("events").add(event_data))

                # Send the message to the agent.
                content = Content(role="user",
                                  parts=[Part.from_text(text=data)])
                live_request_queue.send_content(content=content)
                logger.info("[CLIENT TO AGENT]: %s", data)
            elif mime_type == "audio/pcm":
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(
                    Blob(data=decoded_data, mime_type=mime_type))
            else:
                raise ValueError(f"Mime type not supported: {mime_type}")
    except WebSocketDisconnect:
        logger.info("Client disconnected, closing client->agent messaging.")


@app.get("/")
async def health_check():
    """Simple health check endpoint for Cloud Run."""
    return {"status": "ok"}


async def verify_token(websocket: WebSocket, user_id: str):
    """Verifies the Firebase ID token from the WebSocket connection."""
    token = None
    subprotocols = websocket.scope.get("subprotocols", [])
    if subprotocols:
        token = subprotocols[0]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Missing token")
        return None

    try:
        decoded_token = auth.verify_id_token(token)
        token_user_id = decoded_token["uid"]

        if user_id != token_user_id:
            logger.warning("User ID in path does not match token UID.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                                  reason="User ID mismatch")
            return None
        return token
    except auth.InvalidIdTokenError as e:
        logger.error("Invalid Firebase ID token: %s", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Invalid token")
        return None
    except (ValueError, KeyError) as e:
        logger.error(
            "An unexpected error occurred during token verification: %s", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Token verification failed")
        return None


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str,
        is_audio: str,
):
    """Client websocket endpoint"""
    token = await verify_token(websocket, user_id)
    if not token:
        return

    await websocket.accept(subprotocol=token)
    logger.info("Client #%s connected, audio mode: %s", user_id, is_audio)

    live_events, live_request_queue, session_id = await start_agent_session(
        user_id, app_instance=websocket.app, is_audio=(is_audio == "true"))

    user_has_spoken = asyncio.Event()

    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events, session_id,
                                  user_has_spoken))
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue, session_id,
                                  user_has_spoken))

    done, pending = await asyncio.wait(
        [agent_to_client_task, client_to_agent_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    for task in done:
        if task.exception():
            logger.error("A websocket task finished with an exception:",
                         exc_info=task.exception())

    live_request_queue.close()

    logger.info("Client #%s disconnected", user_id)
