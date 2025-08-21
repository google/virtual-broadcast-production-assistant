"""
Reverse proxy for Agent Engine.

This module implements a reverse proxy for the Agent Engine. It handles both
HTTP and WebSocket traffic, adding Google Cloud authentication to the requests.
"""

import asyncio
import os
import re
from urllib.parse import urlencode

import google.auth
import httpx
from fastapi import (FastAPI, Request, Response, WebSocket)
from google.auth.transport.requests import Request as GoogleAuthRequest
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

app = FastAPI()

AGENT_ENGINE_RESOURCE_NAME = os.environ.get("AGENT_ENGINE_URL")


def get_location_from_resource_name(resource_name):
    """
    Extracts the location from the Agent Engine resource name.

    Args:
        resource_name: The Agent Engine resource name.

    Returns:
        The location string.
    """
    if not resource_name:
        return None
    match = re.search(r"locations/([^/]+)", resource_name)
    if match:
        return match.group(1)
    return None


LOCATION = get_location_from_resource_name(AGENT_ENGINE_RESOURCE_NAME)


def _get_id_token_sync(target_audience):
    """
    Generates a Google Cloud identity token synchronously.

    Args:
        target_audience: The audience for the OIDC identity token.

    Returns:
        The identity token.
    """
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = GoogleAuthRequest()
    creds.with_target_audience(target_audience)
    creds.refresh(auth_req)
    return creds.id_token


async def get_id_token(target_audience):
    """
    Generates a Google Cloud identity token asynchronously.

    Args:
        target_audience: The audience for the OIDC identity token.

    Returns:
        The identity token.
    """
    return await asyncio.to_thread(_get_id_token_sync, target_audience)


@app.websocket("/{path:path}")
async def websocket_proxy(websocket: WebSocket, path: str):
    """
    Proxies WebSocket connections to the Agent Engine.
    """
    await websocket.accept()

    if not LOCATION or not AGENT_ENGINE_RESOURCE_NAME:
        await websocket.close(
            code=1011, reason="AGENT_ENGINE_URL not configured correctly."
        )
        return

    query_string = urlencode(websocket.query_params.multi_items())
    backend_ws_url = (
        f"wss://{LOCATION}-aiplatform.googleapis.com/v1/{AGENT_ENGINE_RESOURCE_NAME}"
        f"{path}"
    )
    if query_string:
        backend_ws_url += f"?{query_string}"

    try:
        id_token = await get_id_token(f"https://{LOCATION}-aiplatform.googleapis.com")
        headers = {"Authorization": f"Bearer {id_token}"}

        async with httpx.AsyncClient() as client:
            async with client.websocket_connect(
                backend_ws_url, extra_headers=headers
            ) as backend_ws:

                async def forward_to_backend():
                    while True:
                        data = await websocket.receive_text()
                        await backend_ws.send_text(data)

                async def forward_to_client():
                    while True:
                        data = await backend_ws.receive_text()
                        await websocket.send_text(data)

                await asyncio.gather(
                    forward_to_backend(),
                    forward_to_client(),
                )
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Authentication error: {e}")
        await websocket.close(code=1011, reason="Authentication error")
    except httpx.HTTPError as e:
        print(f"An error occurred in websocket proxy: {e}")
        await websocket.close(code=1011)


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def http_proxy(path: str, request: Request):
    """
    Proxies HTTP requests to the Agent Engine.
    """
    if not AGENT_ENGINE_RESOURCE_NAME:
        return Response(status_code=500, content="AGENT_ENGINE_URL is not set.")

    try:
        id_token = await get_id_token(f"https://{LOCATION}-aiplatform.googleapis.com")
        headers = dict(request.headers)
        headers["Authorization"] = f"Bearer {id_token}"

        async with httpx.AsyncClient() as client:
            backend_url = (
                f"https://{LOCATION}-aiplatform.googleapis.com/v1/"
                f"{AGENT_ENGINE_RESOURCE_NAME}{path}"
            )

            backend_request = client.build_request(
                method=request.method,
                url=backend_url,
                headers=headers,
                content=await request.body(),
            )

            backend_response = await client.send(backend_request, stream=True)

            return StreamingResponse(
                backend_response.aiter_raw(),
                status_code=backend_response.status_code,
                headers=backend_response.headers,
                background=BackgroundTask(backend_response.aclose),
            )
    except google.auth.exceptions.DefaultCredentialsError as e:
        return Response(status_code=401, content=f"Authentication error: {e}")
    except httpx.HTTPError as e:
        return Response(status_code=500, content=f"An error occurred in http proxy: {e}")
