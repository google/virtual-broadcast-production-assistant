
import asyncio
import os
import re
import httpx
from urllib.parse import urlencode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.auth.transport.httpx import AuthorizedClient

app = FastAPI()

AGENT_ENGINE_RESOURCE_NAME = os.environ.get("AGENT_ENGINE_URL")

def get_location_from_resource_name(resource_name):
    if not resource_name:
        return None
    match = re.search(r"locations/([^/]+)", resource_name)
    if match:
        return match.group(1)
    return None

LOCATION = get_location_from_resource_name(AGENT_ENGINE_RESOURCE_NAME)

@app.websocket("/{path:path}")
async def websocket_proxy(websocket: WebSocket, path: str):
    await websocket.accept()

    if not LOCATION or not AGENT_ENGINE_RESOURCE_NAME:
        await websocket.close(code=1011, reason="AGENT_ENGINE_URL not configured correctly.")
        return

    # Construct the backend WebSocket URL, including query parameters
    query_string = urlencode(websocket.query_params.multi_items())
    backend_ws_url = f"wss://{LOCATION}-aiplatform.googleapis.com/v1/{AGENT_ENGINE_RESOURCE_NAME}{path}"
    if query_string:
        backend_ws_url += f"?{query_string}"
    
    # Use an authorized httpx client that handles auth automatically
    async with AuthorizedClient() as client:
        try:
            async with client.websocket_connect(backend_ws_url) as backend_ws:
                # Coroutine to forward messages from client to backend
                async def forward_to_backend():
                    while True:
                        data = await websocket.receive_text()
                        await backend_ws.send_text(data)

                # Coroutine to forward messages from backend to client
                async def forward_to_client():
                    while True:
                        data = await backend_ws.receive_text()
                        await websocket.send_text(data)

                await asyncio.gather(
                    forward_to_backend(),
                    forward_to_client(),
                )
        except Exception as e:
            print(f"An error occurred in websocket proxy: {e}")
            await websocket.close(code=1011)
