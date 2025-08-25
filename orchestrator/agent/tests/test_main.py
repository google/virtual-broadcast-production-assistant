import pytest
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from broadcast_orchestrator.main import app
from firebase_admin import auth, _apps, initialize_app, firestore


@pytest.fixture(autouse=True)
def mock_firebase_admin(mocker):
    """Mock firebase_admin setup."""
    if not _apps:
        mocker.patch("firebase_admin.initialize_app")
    mocker.patch("firebase_admin.get_app")
    mocker.patch("firebase_admin.firestore.client")
    mocker.patch("firebase_admin.firestore_async.client")
    mocker.patch("broadcast_orchestrator.main.seed_agent_status")
    yield


@pytest.fixture(name="client")
def client_fixture():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@patch("broadcast_orchestrator.main.start_agent_session", new_callable=AsyncMock)
@patch("broadcast_orchestrator.main.auth.verify_id_token")
def test_websocket_valid_token(mock_verify_id_token, mock_start_agent_session, client):
    """Test that a WebSocket connection is accepted with a valid token."""
    mock_verify_id_token.return_value = {"uid": "test_user"}
    mock_start_agent_session.return_value = (AsyncMock(), AsyncMock(), "test_session")
    with client.websocket_connect(
        "/ws/test_user?is_audio=false", subprotocols=["valid_token"]
    ) as websocket:
        websocket.close()


def test_websocket_missing_token(client):
    """Test that a WebSocket connection is rejected if no token is provided."""
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/test_user?is_audio=false"):
            pass  # pragma: no cover
    assert excinfo.value.code == 1008


@patch("broadcast_orchestrator.main.auth.verify_id_token")
def test_websocket_invalid_token(mock_verify_id_token, client):
    """Test that a WebSocket connection is rejected with an invalid token."""
    mock_verify_id_token.side_effect = auth.InvalidIdTokenError("Invalid token")
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/ws/test_user?is_audio=false", subprotocols=["invalid_token"]
        ):
            pass  # pragma: no cover
    assert excinfo.value.code == 1008


@patch("broadcast_orchestrator.main.auth.verify_id_token")
def test_websocket_user_id_mismatch(mock_verify_id_token, client):
    """Test that a WebSocket is rejected if the user ID does not match the token."""
    mock_verify_id_token.return_value = {"uid": "another_user"}
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/ws/test_user?is_audio=false", subprotocols=["valid_token"]
        ):
            pass  # pragma: no cover
    assert excinfo.value.code == 1008
