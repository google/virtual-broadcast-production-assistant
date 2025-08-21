"""
Derived very much from the adk-docs site
https://google.github.io/adk-docs/streaming/custom-streaming-ws/
"""

import json
import asyncio
import base64
import firebase_admin
from firebase_admin import auth, firestore
import warnings
import logging
import os

from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import Runner
from google.adk.sessions import VertexAiSessionService
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status

from .agent import root_agent

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Configure logging to show messages from all modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

#
# ADK Streaming
#

# Load Gemini API Key
load_dotenv()

#
# FastAPI web app
#

app = FastAPI()
session_service: VertexAiSessionService | None = None


@app.on_event("startup")
async def startup_event():
    """
    This function is called when the application starts.
    It's a good place to initialize resources like the Firebase Admin SDK.
    """
    try:
        # Check if the app is already initialized to avoid errors.
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized successfully.")

        global session_service
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION")
        agent_engine_resource_name = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")

        if project_id and location and agent_engine_resource_name:
            session_service = VertexAiSessionService(
                project=project_id,
                location=location,
                agent_engine_id=agent_engine_resource_name,
            )
            logger.info("Vertex AI Session Service initialized.")
        else:
            logger.warning("Could not initialize Vertex AI Session Service due to missing environment variables.")

    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK or Vertex AI Session Service: {e}")


APP_NAME = "ADK Streaming example"


async def start_agent_session(user_id, is_audio=False):
    """Starts an agent session"""

    # Create a Runner
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    # Create a Session
    # The user_id is required by the agent's `before_agent_callback` to
    # fetch user-specific preferences. We pass it in the session's state
    # so it's available in the callback context.
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, state={"user_id": user_id})

    # Set response modality
    modality = "AUDIO" if is_audio else "TEXT"
    run_config = RunConfig(response_modalities=[modality])

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = runner.run_live(
        user_id=user_id,
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


async def agent_to_client_messaging(websocket, live_events):
    """Agent to client communication"""
    try:
        async for event in live_events:

            # If the turn complete or interrupted, send it
            if event.turn_complete or event.interrupted:
                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                logger.info("[AGENT TO CLIENT]: %s", message)
                continue

            # Read the Content and its first Part
            part: Part = (event.content and event.content.parts
                          and event.content.parts[0])
            if not part:
                continue

            # If it's audio, send Base64 encoded audio data
            is_audio = part.inline_data and part.inline_data.mime_type.startswith(
                "audio/pcm")
            if is_audio:
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

            # If it's text and a parial text, send it
            if part.text and event.partial:
                message = {"mime_type": "text/plain", "data": part.text}
                await websocket.send_text(json.dumps(message))
                logger.info("[AGENT TO CLIENT]: text/plain: %s", message)
    except WebSocketDisconnect:
        logger.info("Client disconnected, closing agent->client messaging.")


async def client_to_agent_messaging(websocket, live_request_queue):
    """Client to agent communication"""
    try:
        while True:
            # Decode JSON message
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            mime_type = message["mime_type"]
            data = message["data"]

            # Send the message to the agent
            if mime_type == "text/plain":
                # Send a text message
                content = Content(role="user",
                                  parts=[Part.from_text(text=data)])
                live_request_queue.send_content(content=content)
                logger.info("[CLIENT TO AGENT]: %s", data)
            elif mime_type == "audio/pcm":
                # Send an audio data
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


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str,
        is_audio: str,
        token: str | None = Query(default=None),
):
    """Client websocket endpoint"""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Missing token")
        return

    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        token_user_id = decoded_token["uid"]

        # Ensure the user_id in the path matches the one in the token
        if user_id != token_user_id:
            logger.warning("User ID in path does not match token UID.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                                  reason="User ID mismatch")
            return
    except auth.InvalidIdTokenError as e:
        logger.error("Invalid Firebase ID token: %s", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Invalid token")
        return
    except Exception as e:
        logger.error(
            "An unexpected error occurred during token verification: %s", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                              reason="Token verification failed")
        return

    # Wait for client connection
    await websocket.accept()
    logger.info("Client #%s connected, audio mode: %s", user_id, is_audio)

    # Start agent session
    live_events, live_request_queue = await start_agent_session(
        user_id, is_audio == "true")

    # Start tasks
    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events))
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue))

    # Wait until the websocket is disconnected or an error occurs
    done, pending = await asyncio.wait(
        [agent_to_client_task, client_to_agent_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # If one task finishes, cancel the other one.
    for task in pending:
        task.cancel()

    # Log any exceptions that might have caused a task to finish.
    for task in done:
        if task.exception():
            logger.error("A websocket task finished with an exception:",
                         exc_info=task.exception())

    # Close LiveRequestQueue
    live_request_queue.close()

    # Disconnected
    logger.info("Client #%s disconnected", user_id)
