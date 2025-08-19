import asyncio
import os
from a2a.skills.skill_declarations import AgentSkill
from a2a.cards.agent_card import AgentCard, AgentCapabilities
from a2a.server.server import AgentServer
from .task_manager import AgentTaskManager

# Define the agent's skill
skill = AgentSkill(
    id="ShureAudioAgent",
    name="ShureAudioAgent",
    description="Agent to manage Shure Audio device settings, user presets, and microphone channel coverage via GraphQL.",
    tags=["audio", "shure", "microphone", "presets", "eq", "positioning"],
    examples=[
        "Get the current status of the Shure Audio device",
        "Load user preset '5.1'",
        "Set EQ settings for certain channels according to channel name",
        "Start auto positioning for certain channel",
        "Steer lobe to specific direction - align horizonally"
        "Set microphone channel coverage for coordinates",
    ]
)

# Get host and port from environment or use defaults
host = os.getenv("A2A_HOST", "localhost")
port = int(os.getenv("A2A_PORT", "8080"))

# Define the agent's card
agent_card = AgentCard(
    name="ShureAudioAgent",
    description="Agent designed to manage Shure Audio device settings, user presets, and microphone channel coverage via GraphQL.",
    url=f"http://{host}:{port}/",
    version="1.0.0",
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
    supportsAuthenticatedExtendedCard=True,
)

async def main():
    """Main entry point for the A2A server."""
    task_manager = AgentTaskManager()
    
    server = AgentServer(
        agent_card=agent_card,
        task_manager=task_manager,
        host=host,
        port=port
    )
    
    print(f"Starting ShureAudioAgent A2A server on {host}:{port}")
    await server.start()

if __name__ == "__main__":
    asyncio.run(main()) 