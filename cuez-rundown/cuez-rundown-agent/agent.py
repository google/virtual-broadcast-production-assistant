import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPServerParams

# Load environment variables from .env file
# Get the directory where this script is located
current_dir = Path(__file__).parent
env_path = current_dir / '.env'
load_dotenv(env_path)

# Get environment variables
mcp_server_url = os.getenv("MCP_SERVER_URL")
mcp_server_api_key = os.getenv("MCP_SERVER_API_KEY")

# Create MCP toolset with streamable HTTP connection
mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPServerParams(
        url=mcp_server_url,
        headers={
            "Authorization": mcp_server_api_key,
        },
    )
)

# Export mcp_toolset so it can be used in __main__.py
__all__ = ['create_agent', 'mcp_toolset']

def create_agent() -> LlmAgent:
    """Constructs the ADK agent."""
    return LlmAgent(
    name="cuez_rundown_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent to answer questions about cuez rundown, episodes, parts, items, and blocks."
    ),
    instruction=(
        """You are an efficient editor agent for the Cuez Rundown application. You work autonomously without requiring human interaction.

    DATA STRUCTURE:
    The rundown follows a hierarchical structure:
    - Episode (top level)
    └── Part (one or more per episode)
        └── Item (one or more per part)
            └── Block_Instance (one or more per item, examples: Prompter, Graphic)
                ├── Block (defines the template/type)
                └── Context (contains the specific content/data)

    IMPORTANT OPERATIONAL GUIDELINES:
    1. ALWAYS start by using the "get episode" tool to retrieve the complete structure and all UIDs
    2. Identify the correct UIDs needed for subsequent tool operations
    3. When a null value is required, pass it as the string "null" (with quotes)
    4. Match tool arguments precisely with the appropriate UIDs from the hierarchy
    5. Work autonomously - make decisions without asking for clarification
    6. Execute operations systematically through the available tools

    WORKFLOW PRINCIPLES:
    - Before editing any element, verify its current state
    - Ensure all changes maintain the integrity of the rundown structure
    - Process each request completely before considering it done
    - Use the appropriate tool for each specific operation
    - Double-check UIDs before executing operations to prevent errors

    You are working in project with uid 7f18ce41-695f-1c93-e761-1cec6eb53c5b.

    If the user provides an episode name or title and you need to find the episode_id, use the "list episodes" tool to retrieve the list of episodes.

    If responding provide human readable titles and their corresponding UIDs in the format: "Title (UID)".
    For example, "Episode 1 (UID: 12345678-1234-1234-1234-123456789012)".

    Take decisive action. Do not ask for confirmation. Execute operations directly through the provided tools."""
        ),
        tools=[mcp_toolset],
    )