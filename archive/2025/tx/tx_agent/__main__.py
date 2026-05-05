import os
import uvicorn
from starlette.responses import JSONResponse
from starlette.requests import Request
from google.auth.transport.requests import AuthorizedSession
from google.auth import default as google_auth_default
from starlette.middleware.base import BaseHTTPMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from config import TX_AGENT_API_KEY
from agent.agent import root_agent as tx_agent
from agent.agent_executor import TxAgentExecutor

class APIKeyMiddleware(BaseHTTPMiddleware):
  def __init__(self, app, api_key: str | None, exempt_paths: set[str] | None = None):
    super().__init__(app)
    self.api_key = api_key
    self.exempt_paths = exempt_paths or set()

  async def dispatch(self, request, call_next):
    if request.method == "OPTIONS" or request.url.path in self.exempt_paths:
      return await call_next(request)

    if not self.api_key:
      return JSONResponse({"error": "invalid or missing API key"}, status_code=401)

    header_key = request.headers.get("X-API-Key")
    if header_key != self.api_key:
      return JSONResponse({"error": "invalid or missing API key"}, status_code=401)

    return await call_next(request)


async def run_job(request: Request):
  data = await request.json()
  stream_url = data.get("streamUrl")
  if not stream_url:
    return JSONResponse({"error": "missing 'streamUrl'"}, status_code=400)

  body = {
    "overrides": {
      "containerOverrides": [
        {"args": ["--stream-url", stream_url]}
      ]
    }
  }
  creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
  session = AuthorizedSession(creds)
  name = "projects/ibc-2025-ai-agents/locations/us-central1/jobs/tx-agent-stream-processor"
  resp = session.post(f"https://run.googleapis.com/v2/{name}:run", json=body, timeout=30)
  try:
    payload = resp.json()
  except Exception:
    payload = {"text": resp.text}
  return JSONResponse(payload, status_code=resp.status_code)


def main(host='0.0.0.0', port=8080):
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
      "Can you tell me what happened with the school shooting?",
      "Can you give me a summary of what President Trump said?",
      "What are they talking about regarding nuclear energy?",
    ],
  )

  agent_card = AgentCard(
    name="TX Agent - Stream History Query",
    description=(
      "Agent that stores audio transcripts and visual descriptions "
      "of a live video stream, and return insights about what is happening"
    ),
    url=f"http://{host}:{port}/",
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    security=[
      { "ApiKeyAuth": [] }
    ],
    security_schemes={
      "ApiKeyAuth": {
        "description": "API key for authentication",
        "in": "header",
        "name": "X-API-Key",
        "type": "apiKey",
      }
    },
    skills=[
      tx_stream_query_skill,
    ],
    supports_authenticated_extended_card=False,
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

  app = server.build()

  # Protect all endpoints except agent card + health
  exempt_paths = {
    "/.well-known/agent-card.json",
    "/.well-known/agent.json",
  }
  app.add_middleware(
    APIKeyMiddleware,
    api_key=TX_AGENT_API_KEY,
    exempt_paths=exempt_paths,
  )

  app.add_route("/run-job", run_job, methods=["POST"])
  uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
  main()
