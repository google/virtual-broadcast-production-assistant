from google.adk.agents import Agent
from . import prompts
from .vector_search_tool import vector_search

root_agent = Agent(
  name="tx_agent",
  model="gemini-2.5-flash",
  description=prompts.ROOT_PROMPT,
  instruction=prompts.INSTRUCTIONS,
  tools=[vector_search],
)
