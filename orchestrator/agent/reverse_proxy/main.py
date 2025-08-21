import asyncio
import os
import re
import httpx
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest

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
STREAM_QUERY_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{AGENT_ENGINE_RESOURCE_NAME}:streamQuery" if LOCATION else None

# Global Auth object
creds, project = google_auth_default()

def get_auth_token():
    # See if the credentials can be refreshed
    if creds.token is None or creds.expired:
        creds.refresh(GoogleAuthRequest())
    return creds.token

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def http_proxy(request: Request, path: str):
    # This http_proxy is likely incorrect as well, but the user's focus is on websockets.
    # I will leave it as is for now, but it has the same issue of not constructing the URL correctly.
    # A proper implementation would need to know if it's a query or streamQuery.
    # For now, I will focus on the websocket part.
    async with httpx.AsyncClient() as client:
        # This is still wrong, but I'm not fixing it as part of this request.
        url = f"{AGENT_ENGINE_RESOURCE_NAME}/{path}"
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

    if not STREAM_QUERY_URL:
        await websocket.close(code=1011, reason="AGENT_ENGINE_URL not configured correctly.")
        return

    try:
        # The first message from the client should contain the query.
        query = await websocket.receive_text()

        headers = {
            "Authorization": f"Bearer {get_auth_token()}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", STREAM_QUERY_URL, headers=headers, json={"query": query}, timeout=None) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    await websocket.send_text(f"Error: {response.status_code} - {error_text.decode()}")
                    await websocket.close()
                    return

                async for chunk in response.aiter_bytes():
                    await websocket.send_bytes(chunk)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011, reason="An internal error occurred.")
    finally:
        if not websocket.client_state.value == 3: # CLOSED
             await websocket.close()