
import os
import httpx
from fastapi import FastAPI, Request, Response, WebSocket

app = FastAPI()

AGENT_ENGINE_URL = os.environ.get("AGENT_ENGINE_URL")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def http_proxy(request: Request, path: str):
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
    async with httpx.AsyncClient() as client:
        url = f"{AGENT_ENGINE_URL.replace('http', 'ws', 1)}/{path}"
        async with client.websocket_connect(url) as backend_ws:
            async def forward_to_backend():
                while True:
                    data = await websocket.receive_text()
                    await backend_ws.send_text(data)

            async def forward_to_client():
                while True:
                    data = await backend_ws.receive_text()
                    await websocket.send_text(data)

            import asyncio
            await asyncio.gather(
                forward_to_backend(),
                forward_to_client(),
            )
