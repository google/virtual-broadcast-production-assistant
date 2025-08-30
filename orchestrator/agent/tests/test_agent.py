import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from a2a.types import AgentCard

from orchestrator.agent.broadcast_orchestrator.agent import RoutingAgent

@pytest.fixture
def mock_agent_card():
    """Fixture for a mock AgentCard."""
    return AgentCard(
        name="Test Agent",
        url="http://test.com",
        description="A test agent",
        capabilities={},
        defaultInputModes=[],
        defaultOutputModes=[],
        skills=[],
        version="1.0"
    )

@pytest.fixture
def mock_callback_context():
    """Fixture for a mock CallbackContext."""
    context = MagicMock()
    context.state = {}
    return context

@pytest.mark.asyncio
@patch("orchestrator.agent.broadcast_orchestrator.agent.load_system_instructions")
@patch("orchestrator.agent.broadcast_orchestrator.agent.get_all_agents")
@patch("firebase_admin.firestore_async.client")
async def test_before_agent_callback_loads_agents_successfully(
    mock_firestore_client, mock_get_all_agents, mock_load_instructions, mock_agent_card, mock_callback_context
):
    """
    Tests that before_agent_callback successfully loads online agents
    from Firestore.
    """
    # Arrange
    agent = RoutingAgent()

    mock_get_all_agents.return_value = [
        {
            "id": "agent1",
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://agent1.com/a2a"
        },
        {
            "id": "agent2",
            "status": "offline", # Should be skipped
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://agent2.com/a2a"
        }
    ]

    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Act
    await agent.before_agent_callback(mock_callback_context)

    # Assert
    assert len(agent.remote_agent_connections) == 1
    assert "agent1" in agent.remote_agent_connections
    assert "agent2" not in agent.remote_agent_connections
    assert "agent1" in agent.cards


@pytest.mark.asyncio
@patch("orchestrator.agent.broadcast_orchestrator.agent.load_system_instructions")
@patch("orchestrator.agent.broadcast_orchestrator.agent.get_all_agents")
@patch("firebase_admin.firestore_async.client")
async def test_before_agent_callback_handles_rundown_agent(
    mock_firestore_client, mock_get_all_agents, mock_load_instructions, mock_agent_card, mock_callback_context
):
    """
    Tests that before_agent_callback correctly identifies and handles the
    preferred rundown agent.
    """
    # Arrange
    agent = RoutingAgent()
    mock_callback_context.state = {"user_id": "test_user"}

    # The preferred rundown agent is CUEZ_RUNDOWN_AGENT
    mock_get_all_agents.return_value = [
        {
            "id": "CUEZ_RUNDOWN_AGENT",
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://cuez.com/a2a"
        },
        {
            "id": "some_other_agent",
            "status": "online",
            "card": mock_agent_card.model_dump(),
            "a2a_endpoint": "http://other.com/a2a"
        }
    ]

    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"rundown_system": "cuez"}
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Act
    await agent.before_agent_callback(mock_callback_context)

    # Assert
    assert "rundown_agent_connection" in mock_callback_context.state
    assert mock_callback_context.state["rundown_agent_config_name"] == "CUEZ_RUNDOWN_AGENT"
    # Check that the rundown agent is not in the general available_agents_list
    assert "CUEZ_RUNDOWN_AGENT" not in mock_callback_context.state["available_agents_list"]
    assert "some_other_agent" in mock_callback_context.state["available_agents_list"]
