"""Tests for the reverse proxy application."""

import os
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient


# This fixture will be active for all tests in this file
@pytest.fixture(autouse=True)
def set_env_var():
    """Sets a dummy environment variable for the AGENT_ENGINE_URL."""
    with patch.dict(os.environ, {
        "AGENT_ENGINE_URL": "projects/proj/locations/loc/reasoningEngines/123"
    }):
        yield


@patch("reverse_proxy.main.get_id_token",
       new_callable=AsyncMock,
       return_value="dummy-token")
def test_http_proxy_get(mock_get_token):
    """Tests that a simple GET request to the HTTP proxy endpoint works."""
    # pylint: disable=import-outside-toplevel, import-error
    from reverse_proxy.main import app
    client = TestClient(app)

    # We patch the backend call to avoid real network requests
    with patch("reverse_proxy.main.httpx.AsyncClient.send") as mock_send:
        # To mock a streaming response, we need to mock the response object
        # and its `aiter_raw` method, which must be an async generator.
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.aclose = AsyncMock()

        async def content_stream():
            yield b'{"status":"ok"}'

        mock_response.aiter_raw = content_stream
        mock_send.return_value = mock_response

        response = client.get("/agent-engine/some/path")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_get_token.assert_called_once()


@patch("reverse_proxy.main.get_id_token",
       new_callable=AsyncMock,
       return_value="dummy-token")
def test_websocket_proxy_flow(mock_get_token):
    """
    Tests the full bidirectional flow of a WebSocket connection through the proxy.
    """
    # pylint: disable=import-outside-toplevel, import-error
    from reverse_proxy.main import app
    client = TestClient(app)

    # Patch the `websockets.connect` function in the main module
    with patch("reverse_proxy.main.websockets.connect") as mock_connect:
        # Configure the mock to simulate a backend websocket connection
        mock_backend_ws = AsyncMock()
        mock_backend_ws.recv.return_value = "Hello from backend"
        mock_connect.return_value.__aenter__.return_value = mock_backend_ws

        # Use the TestClient to establish a websocket connection to our proxy
        with client.websocket_connect("/agent-engine/ws/test") as client_ws:
            # 1. Send a message from the client
            client_ws.send_text("Hello from client")

            # 2. Wait for the response from the backend (via the proxy).
            response = client_ws.receive_text()
            assert response == "Hello from backend"

            # 3. Now assert that the backend mock was called correctly.
            mock_backend_ws.send.assert_called_once_with("Hello from client")

        # Verify that the connection to the backend was made with the correct URL
        mock_connect.assert_called_once()
        mock_get_token.assert_called_once()
        called_args, _ = mock_connect.call_args
        expected_url = ( # Break up long line
            "wss://loc-aiplatform.googleapis.com/v1/"
            "projects/proj/locations/loc/reasoningEngines/123/agent-engine/ws/test"
        )
        assert expected_url in called_args
