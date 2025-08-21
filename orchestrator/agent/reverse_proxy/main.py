
import asyncio
import os
import httpx
from fastapi import FastAPI, Request, Response, WebSocket

app = FastAPI()

# We expect this to be the base URL of the agent engine's websocket endpoint.
# We are still trying to find out what this URL is.
AGENT_ENGINE_URL = os.environ.get("AGENT_ENGINE_URL")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def http_proxy(request: Request, path: str):
    # This proxy is likely incorrect and needs to be fixed once we know the agent's URL.
    # For now, we focus on the websocket part.
    if not AGENT_ENGINE_URL:
        return Response(status_code=500, content="AGENT_ENGINE_URL not configured")

    async with httpx.AsyncClient() as client:
        url = f"{AGENT_ENGINE_URL}/{path}"
        headers = dict(request.headers)
        headers.pop("host", None)
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
        )
        return Response(content=response.content, status_code=response.status_code, headers=response.headers)

@app.websocket("/{path:path}")
async def websocket_proxy(websocket: WebSocket, path: str):
    await websocket.accept()

    if not AGENT_ENGINE_URL:
        await websocket.close(code=1011, reason="AGENT_ENGINE_URL not configured")
        return

    # The agent has a /ws/{user_id} endpoint. The path from the incoming request
    # should be forwarded.
    # We need to construct the correct ws/wss URL.
    # Let's assume AGENT_ENGINE_URL is a http/https URL.
    ws_url = AGENT_ENGINE_URL.replace("http", "ws", 1)
    full_ws_url = f"{ws_url}{path}" # The path should be /ws/{user_id}

    async with httpx.AsyncClient() as client:
        try:
            async with client.websocket_connect(full_ws_url) as backend_ws:
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
