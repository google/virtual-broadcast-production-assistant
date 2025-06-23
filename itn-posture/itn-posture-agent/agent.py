import click
import uvicorn

from agent_executor import ADKAgentExecutor

from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (AgentCapabilities, AgentCard, AgentSkill)

from google.adk.agents import Agent

from dotenv import load_dotenv

load_dotenv()

@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=10002)
def main(host: str, port: int):
    
  ## Sequence Skill
  seq_skill = AgentSkill(
    id="seq",
    name="Sequence",
    description="Checks sequencing orders of graphics",
    tags=["graphics", "order", "compliance"],
    examples=["00:01 -> 00:00"],
  )
  
  ## Fact Check Skill
  fact_skill = AgentSkill(
    id="fact",
    name="Fact Check",
    description="Checks factual information within graphics",
    tags=["graphics", "fact"],
    examples=["The moon landing was on 3rd February 2003"],
  )
  
  ## Spell Check Skill
  spell_skill = AgentSkill(
    id="spell",
    name="Spell Check",
    description="Spell checks graphical text",
    tags=["graphics", "fact"],
    examples=["Speling"],
  )

  ## ITN Posture Agent Card
  agent_card = AgentCard(
    name="itn-posture-agent",
    description="Provides Stack Checking Services",
    url=f"http://{host}:{port}/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[seq_skill, fact_skill, spell_skill]
  )
  
  ## ITN Posture Agent
  adk_agent = Agent(
    name="itn_posture_agent",
    model="gemini-2.0-flash",
    description=("Provides agentic access to the ITN Posture running order service"),
    instruction="You are a helpful senior assistant used to interact with the Posture running order error checking service for a UK broadcaster. "
                "There are four types of check completed: 'spelling', 'sequence', 'factual', 'enhancement'. "
                "The running order is made up of stories, and stories are made up of elements (viz_graphic, text, closed_caption, presenter_instruction). "
                "Spelling is completed by the bing spellcheck API, sequence is if the graphical elements are out of order based on their timings, both factual and enhancement are returns from Perplexity AI and are therefore unstructured text strings. "
                "When the user asks what stacks or running orders are available use the 'GetStacks' tool to find this information. "
                "When the user asks for overall error information about a stack (such as how many spelling or sequence errors) use the 'GetStackStats' tool, you MUST get the stackId from the 'GetStacks' output first. "
                "NEVER ask the user for the stackId directly, it is your job to convert the label (such as C4 news) to the appropriate stack ID using 'GetStacks'. "
                "When the user asks for information about a specific story, or errors within a specific story (such as are there any sequence errors in ...) use the 'GetStack' tool and filter it down by the story OR ERROR requested, you MUST get the stackId from the 'GetStacks' output first."
                "When using GetStack, if the user has not requested a specific story you can summarise all the stories and how many errors they have, including what kind of errors. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the result clearly and in natural terms. "
                "C3, C4, C5 are short nicknames for ITV, Channel 4, Channel 5. In addition, never show the stackId to the user, it is a backend UUIDv4 that should not concern the user. Instead use the label of the stack. "
                "NEVER display verbose information to the user, always summarise or bullet point out the answer, in addition do not directly output a response such as 'Count: 1 [Out Time is Before In Time]' it must be in natural terms.",
    tools=[],
  )
  
  ## The Agent Runner which will manage agent state
  runner = Runner(
    app_name=agent_card.name,
    agent=adk_agent,
    artifact_service=InMemoryArtifactService(),
    session_service=InMemorySessionService(),
    memory_service=InMemoryMemoryService(),
  )
  
  ## 
  agent_executor = ADKAgentExecutor(runner, agent_card)
  request_handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
  
  ## Hosting services for the agent
  a2a_app = A2AStarletteApplication( agent_card=agent_card, http_handler=request_handler)
  uvicorn.run(a2a_app.build(), host=host, port=port)

if __name__ == "__main__":
  main()