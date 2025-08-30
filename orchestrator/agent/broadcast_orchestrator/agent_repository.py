"""Module for fetching agent data from Firestore."""
import logging
from firebase_admin import firestore_async

logger = logging.getLogger(__name__)


async def get_all_agents() -> list[dict]:
    """
    Fetches all agent details from the Firestore 'agent_status' collection.

    Returns:
        A list of agent data dictionaries. Each dictionary includes the
        agent's ID and its corresponding data from Firestore.
    """
    logger.info("Fetching all agent details from Firestore.")
    try:
        db = firestore_async.client()
        agents_ref = db.collection("agent_status")
        agents_stream = agents_ref.stream()
        agents = []
        async for agent in agents_stream:
            agent_data = agent.to_dict()
            agent_data["id"] = agent.id
            agents.append(agent_data)
        logger.info("Successfully fetched %d agents.", len(agents))
        return agents
    except Exception as e:
        logger.error("Failed to fetch agents from Firestore: %s", e)
        return []
