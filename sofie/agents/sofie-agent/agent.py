import logging
import os

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent

load_dotenv()

logging.basicConfig()

HOST = os.getenv("HOST")

# Create MCP toolset with streamable HTTP connection
mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPServerParams(
        url=HOST
    )
)

# Export mcp_toolset so it can be used in __main__.py
__all__ = ['create_agent', 'mcp_toolset']


def load_instructions_from_file(filename):
    """
    Load agent instructions from a markdown file.
    
    Args:
        filename (str): Path to the markdown file containing instructions.
        
    Returns:
        str: The instruction text from the file.
    """
    possible_paths = [
        filename,  # Direct filename
        os.path.join(os.path.dirname(__file__), filename),  # Same directory as script
        os.path.abspath(filename),  # Absolute path
        os.path.join(os.getcwd(), filename)  # Current working directory
    ]
    
    # Try each path
    for path in possible_paths:
        try:
            print(f"Trying to load instructions from: {path}")
            if os.path.exists(path):
                with open(path, 'r') as file:
                    instructions = file.read()
                print(f"Successfully loaded instructions from {path}")
                return instructions
        except Exception as e:
            print(f"Error loading instructions from {path}: {e}")

    # Fallback return if no paths succeed
    return "Your instructions are not available at the moment. Tell the user they haven't loaded"
# Load instructions from external file
agent_instructions = load_instructions_from_file('agent_instructions.md')

# Path to your Sofie MCP server
SOFIE_MCP_PATH = os.path.join(os.path.dirname(__file__), "../", "sofie-tool")
print (SOFIE_MCP_PATH)
WEBSITE_MCP_PATH = os.path.join(os.path.dirname(__file__), "../../../orchestrator/frontend")

def create_agent() -> LlmAgent:
    """Constructs the ADK agent."""
    return LlmAgent(
    name="sofie_agent",
    model="gemini-2.0-flash-ext",
    description=(
        "An agent built to assist with the Sofie Rundown application"
    ),
    instruction=agent_instructions,
        tools=[mcp_toolset],
    )