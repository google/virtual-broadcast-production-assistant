import os
import uvicorn
from agent import root_agent as frontend_data_agent

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from agent_executor import ActivityAgentExecutor

def create_app():
    data_reformatting_skill = AgentSkill(
        id="data_reformatting_skill",
        name="Data Reformatting",
        description=(
        "Reformats incoming data into a structured format suitable for storage."
        ),
        tags=[
        "data",
        "reformatting",
        "storage"
        ],
        examples=[
        "Unstructured data"
        ],
    )

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))

    agent_card = AgentCard(
        name="Activity Agent",
        description=(
        "Agent that takes in data from other agents and reformats it into a set pattern "
        "which can then be inserted into a datastore."
        ),
        url=f"http://{host}:{port}/",
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
        data_reformatting_skill,
        ],
    )

    request_handler = DefaultRequestHandler(
        task_store=InMemoryTaskStore(),
        agent_executor=ActivityAgentExecutor(
        agent=frontend_data_agent,
        ),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    return server.build()

app = create_app()

if __name__ == "__main__":
  uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
