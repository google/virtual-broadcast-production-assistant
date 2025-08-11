from google.adk.agents import Agent
import prompts
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import os

from dotenv import load_dotenv

load_dotenv()
WEBSITE_MCP_PATH = "./tools/"

root_agent = Agent(
  name="frontend_data_agent",
  model="gemini-2.5-flash",
  description=prompts.ROOT_PROMPT,
  instruction=prompts.INSTRUCTIONS,
  tools=[
      # Website MCP
      MCPToolset(
          connection_params=StdioServerParameters(
              command='node',
              args=[os.path.join(WEBSITE_MCP_PATH, 'server.js')],
          ),
      ),
  ]
)
