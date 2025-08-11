from google.adk.agents import Agent
import prompts
from vector_search_tool import vector_search

from dotenv import load_dotenv

load_dotenv()


root_agent = Agent(
  name="frontend_data_agent",
  model="gemini-2.5-flash",
  description=prompts.ROOT_PROMPT,
  instruction=prompts.INSTRUCTIONS,
  tools=[vector_search],
)
