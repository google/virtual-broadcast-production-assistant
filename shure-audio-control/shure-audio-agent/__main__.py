"""
Main entry point for the Shure Audio Control Agent

This module starts the agent server and handles command-line arguments.
"""

import logging
import os
import asyncio

import click
import uvicorn

from .agent import create_agent
from .agent_executor import ADKAgentExecutor
from .audio_control import get_audio_controller
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from starlette.routing import Route

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from starlette.applications import Starlette


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="localhost", help="Host to bind the server to")
@click.option("--port", "port", default=10003, help="Port to bind the server to")
@click.option("--log-level", "log_level", default="INFO", help="Logging level")
def main(host: str, port: int, log_level: str):
    """Start the Shure Audio Control Agent server."""
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    # Verify Azure OpenAI configuration
    required_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_NAME"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "Please set them in your .env file or environment."
        )
    
    logger.info("Starting Shure Audio Control Agent...")
    logger.info(f"Azure OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
    
    # Define agent skills
    skills = [
        AgentSkill(
            id="get_channel_status",
            name="Get Channel Status",
            description="Get the current status of audio channels including gain, mute, and phantom power settings.",
            tags=["audio", "channels", "status"],
            examples=[
                "What's the status of channel 1?",
                "Show me all channel levels",
                "Are any channels muted?"
            ],
        ),
        AgentSkill(
            id="set_channel_gain",
            name="Set Channel Gain",
            description="Adjust the gain level for specific audio channels.",
            tags=["audio", "gain", "volume"],
            examples=[
                "Set channel 1 gain to -12 dB",
                "Increase the level on channel 2",
                "Adjust microphone gain"
            ],
        ),
        AgentSkill(
            id="mute_control", 
            name="Mute Control",
            description="Mute or unmute audio channels.",
            tags=["audio", "mute", "control"],
            examples=[
                "Mute channel 3",
                "Unmute all channels",
                "Turn off the host microphone"
            ],
        ),
        AgentSkill(
            id="phantom_power",
            name="Phantom Power Control", 
            description="Enable or disable phantom power for condenser microphones.",
            tags=["audio", "phantom", "power", "microphone"],
            examples=[
                "Enable phantom power on channel 1",
                "Turn off phantom power for channel 2",
                "Which channels have phantom power enabled?"
            ],
        ),
        AgentSkill(
            id="audio_presets",
            name="Audio Presets",
            description="Apply predefined audio configurations for different broadcast scenarios.",
            tags=["audio", "presets", "configuration"],
            examples=[
                "Apply broadcast news preset",
                "Set up for live sports commentary",
                "Reset all channels to default"
            ],
        ),
        AgentSkill(
            id="device_info",
            name="Device Information",
            description="Get information about the connected Shure audio device.",
            tags=["device", "status", "information"],
            examples=[
                "What's the device model?",
                "Show device status",
                "Check connection status"
            ],
        ),
    ]

    # Create agent card
    agent_card = AgentCard(
        name="Shure Audio Control Agent",
        description="Controls Shure audio equipment for broadcast production environments. "
                   "Manages audio channels, gain levels, muting, phantom power, and preset configurations.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
    )

    logger.info(f"Agent card created: {agent_card.name} v{agent_card.version}")

    # Create ADK agent
    try:
        adk_agent = create_agent()
        logger.info("ADK agent created successfully")
    except Exception as e:
        logger.error(f"Failed to create ADK agent: {e}")
        raise

    # Create ADK runner
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    
    logger.info("ADK runner initialized")

    # Create agent executor
    agent_executor = ADKAgentExecutor(runner, agent_card)

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, 
        task_store=InMemoryTaskStore()
    )

    # Create A2A application
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, 
        http_handler=request_handler
    )

    logger.info(f"Starting server on {host}:{port}")
    
    # Initialize audio controller on startup
    async def startup():
        """Initialize audio controller connection."""
        try:
            controller = get_audio_controller()
            connection_status = await controller.connect()
            if connection_status:
                logger.info("Successfully connected to Shure audio device")
            else:
                logger.warning("Failed to connect to Shure audio device - running in simulation mode")
        except Exception as e:
            logger.error(f"Error initializing audio controller: {e}")
    
    # Add startup event
    app = a2a_app.build()
    app.add_event_handler("startup", startup)
    
    # Start the server
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=log_level.lower()
    )


if __name__ == "__main__":
    main() 