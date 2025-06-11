import logging
import os
import asyncio

import uvicorn

from .agent import create_agent, mcp_toolset
from .agent_executor import ADKAgentExecutor
from .mcp_skills import get_skills_from_mcp, get_default_skills
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
)


load_dotenv()

logging.basicConfig(level=logging.INFO)


def main(host: str, port: int):
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI") != "TRUE" and not os.getenv(
        "GOOGLE_API_KEY"
    ):
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set and "
            "GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
        )

    # Get skills from MCP server
    logging.info("Retrieving skills from MCP server...")
    skills = asyncio.run(get_skills_from_mcp(mcp_toolset))
    
    if not skills:
        logging.warning("No skills retrieved from MCP server, using default skills")
        skills = get_default_skills()
    else:
        logging.info(f"Successfully retrieved {len(skills)} skills from MCP server")
        for skill in skills:
            logging.info(f"  - {skill.id}: {skill.name}")

    agent_card = AgentCard(
        name="Cuez Agent",
        description="Helps with the cuez rundown",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
    )

    adk_agent = create_agent()
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    agent_executor = ADKAgentExecutor(runner, agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    uvicorn.run(a2a_app.build(), host=host, port=port)


if __name__ == "__main__":
    main(host="0.0.0.0", port=8001)