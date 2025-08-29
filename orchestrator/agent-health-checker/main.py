"""Checks remote agent status and updates Firestore."""
import asyncio
import os
import sys
import json
import uuid
import httpx
from google.cloud import firestore
from google.cloud import secretmanager
from a2a.client import A2AClient
from a2a.types import (SendMessageRequest, MessageSendParams, Message,
                       TextPart, Part, AgentCard, AgentCapabilities)

# Retrieve Job-defined env vars
TASK_INDEX = os.getenv("CLOUD_RUN_TASK_INDEX", "0")
TASK_ATTEMPT = os.getenv("CLOUD_RUN_TASK_ATTEMPT", "0")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")


class TaskfailException(Exception):
    """Exception to call on task failure"""


def get_current_service_account():
    """Queries the metadata server to get the current service account."""
    try:
        url = (
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            "service-accounts/default/email"
        )
        headers = {"Metadata-Flavor": "Google"}
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return f"Could not retrieve service account email: {e}"


def get_secret(secret_id):
    """Retrieves a secret from Google Cloud Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


async def get_agent_card(client, base_url):
    """Fetches an agent's card from its .well-known URL."""
    card = None
    try:
        # Construct the .well-known URL by removing any trailing slashes
        well_known_url = base_url.rstrip("/") + "/.well-known/agent.json"
        response = await client.get(well_known_url, timeout=5)
        response.raise_for_status()
        card = response.json()

    except httpx.RequestError as e:
        print(f"Error fetching agent.json for {base_url}: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding agent.json for {base_url}: {e}")
    except Exception as e:
        print(
            "An unexpected error occurred while fetching card for "
            f"{base_url}: {e}"
        )
    return card


async def check_agent_health(agent_id, agent_dict):
    """Checks the health of a single agent and extracts capability tags."""
    url = agent_dict.get("url")
    status = "offline"
    card = None
    headers = {}
    a2a_endpoint = None

    if agent_dict.get("api_key_secret"):
        try:
            api_key = get_secret(agent_dict["api_key_secret"])
            headers["X-API-Key"] = api_key
        except Exception as e:
            print(f"Failed to get secret for {agent_id}: {e}")
            return {
                "status": "error",
                "card": None,
                "a2a_endpoint": a2a_endpoint
            }

    if url:
        try:
            async with httpx.AsyncClient(timeout=10,
                                         headers=headers) as client:
                # Fetch the agent card to get the correct a2a_endpoint
                card = await get_agent_card(client, url)

                if card:
                    a2a_endpoint = card.get("url", url)

                    # Step 1: Basic health check using A2A
                    a2a_card = AgentCard(name=agent_id,
                                         url=a2a_endpoint,
                                         description="Health check",
                                         capabilities=AgentCapabilities(),
                                         defaultInputModes=[],
                                         defaultOutputModes=[],
                                         skills=[],
                                         version="1.0")
                    a2a_client = A2AClient(client, a2a_card)
                    message_request = SendMessageRequest(
                        id=str(uuid.uuid4()),
                        params=MessageSendParams(message=Message(
                            messageId=str(uuid.uuid4()),
                            role="user",
                            parts=[Part(root=TextPart(text="Are you there?"))])))
                    response = await a2a_client.send_message(message_request)

                    if response:
                        status = "online"

        except Exception as e:
            print(f"A2A check failed for {agent_id}: {e}")
            status = "offline"

    return {"status": status, "card": card, "a2a_endpoint": a2a_endpoint}


async def main():
    """
    Checks the status of each remote agent and updates Firestore.
    """
    print(
        f"Job is running as service account: {get_current_service_account()}")

    db = firestore.AsyncClient()
    agents_ref = db.collection("agent_status")
    agents = agents_ref.stream()

    health_check_tasks = []
    agent_ids = []
    agent_dicts = []
    found_agents = False
    async for agent in agents:
        found_agents = True
        agent_dict = agent.to_dict()
        agent_ids.append(agent.id)
        agent_dicts.append(agent_dict)
        health_check_tasks.append(check_agent_health(agent.id, agent_dict))

    if not found_agents:
        print("Warning: No documents found in 'agent_status' collection. "
              "Job will exit without performing any updates.")
        return

    results = await asyncio.gather(*health_check_tasks)

    update_tasks = []
    print(f"Preparing to update status for {len(agent_ids)} agent(s)...")
    for agent_id, agent_dict, result in zip(agent_ids, agent_dicts, results):
        update_data = {
            "status": result["status"],
            "last_checked": firestore.SERVER_TIMESTAMP,
            "card": result.get("card"),
        }
        new_a2a_endpoint = result.get("a2a_endpoint")
        if new_a2a_endpoint and agent_dict.get(
                "a2a_endpoint") != new_a2a_endpoint:
            update_data["a2a_endpoint"] = new_a2a_endpoint

        update_tasks.append(
            agents_ref.document(agent_id).update(update_data)
        )
        status = result["status"]
        print(f"Updated status for {agent_id}: {status}")

    await asyncio.gather(*update_tasks)
    print("Firestore updates complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except TaskfailException as err:
        message = (f"Task #{TASK_INDEX}, " +
                   f"Attempt #{TASK_ATTEMPT} failed: {str(err)}")

        print(json.dumps({"message": message, "severity": "ERROR"}))
        sys.exit(1)  # Retry Job Task by exiting the process
