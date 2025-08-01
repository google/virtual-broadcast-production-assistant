import uvicorn
from .agent import root_agent as tx_agent

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from .agent_executor import TxAgentExecutor

def main(host='localhost', port=8010):
  tx_stream_query_skill = AgentSkill(
    id="tx_stream_query_skill",
    name="Query Stream History",
    description=(
      "Searches the history of transcripts and visual descriptions of the live stream"
      "and returns the most relevant information related to the query"
    ),
    tags=[
      "query",
      "history",
      "stream",
      "transcription",
      "visual description"
    ],
    examples=[
      "Can you tell me what happened with the school shooting?"
      "Can you give me a summary of what President Trump said?"
      "What are they talking about regarding nuclear energy?"
    ],
  )

  agent_card = AgentCard(
    name="TX Agent - Stream History Query",
    description=(
      "Agent that stores audio transcripts and visual descriptions"
      "of a live video stream, and return insights about what is happening"
    ),
    url=f"http://{host}:{port}/",
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
      tx_stream_query_skill,
    ],
  )

  request_handler = DefaultRequestHandler(
    task_store=InMemoryTaskStore(),
    agent_executor=TxAgentExecutor(
      agent=tx_agent,
    ),
  )

  server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
  )

  uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
  main()
