from google.adk.agents import Agent
from config import GEMINI_MODEL_FOR_AGENT
from . import prompts
from .vector_search_tool import vector_search

root_agent = Agent(
  name="tx_agent",
  model=GEMINI_MODEL_FOR_AGENT,
  description=prompts.ROOT_PROMPT,
  instruction=prompts.INSTRUCTIONS,
  tools=[vector_search],
)
