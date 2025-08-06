"""
Derived very much from the adk-docs site
https://google.github.io/adk-docs/streaming/custom-streaming-ws/
"""

import json
import asyncio
import base64
import warnings
import logging

from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from broadcast_orchestrator.agent import root_agent

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

APP_NAME = "ADK Streaming example"


async def start_agent_session(user_id, is_audio=False):
    """Starts an agent session"""

    # Create a Runner
    runner = InMemoryRunner(
        app_name=APP_NAME,
        agent=root_agent,
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,  # Replace with actual user ID
    )

    # Set response modality
    modality = "AUDIO" if is_audio else "TEXT"
    run_config = RunConfig(response_modalities=[modality])

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = runner.run_live(
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


#
# FastAPI web app
#

app = FastAPI()


@app.get("/")
async def health_check():
    """Simple health check endpoint for Cloud Run."""
    return {"status": "ok"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int,
                             is_audio: str):
    """Client websocket endpoint"""

    # Wait for client connection
    await websocket.accept()
    logger.info("Client #%d connected, audio mode: %s", user_id, is_audio)

    # Start agent session
    user_id_str = str(user_id)
    live_events, live_request_queue = await start_agent_session(
        user_id_str, is_audio == "true")

    # Start tasks
    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events))
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue))

    # Wait until the websocket is disconnected or an error occurs
    tasks = [agent_to_client_task, client_to_agent_task]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    # Close LiveRequestQueue
    live_request_queue.close()

    # Disconnected
    logger.info("Client #%d disconnected", user_id)
