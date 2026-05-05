# TX-AGENT 

## Test locally

This repository includes a Docker image that starts the agent server (from `__main__.py`).

## Prerequisites
- **Docker Desktop** (or Docker Engine) installed.
- *(Optional, for Firestore/Firebase Admin)* a Google Cloud service account JSON on your host.
- A `.env` file inside `tx_agent/` with the minimal required environment variables (check .env-example).

## Build the Docker image

```bash
docker build -t tx-agent:dev -f Dockerfile .
```

## Start the server container

```bash
# Path to your local SA key
SA_HOST="$HOME/.keys/google/gen-lang-client-0625015479-b1367ab227a4.json"

docker run --rm -p 8080:8080 --name txagent \
  -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  -e GOOGLE_API_KEY=<YOUR_API_KEY> \
  -e FIRESTORE_DB_COLLECTION=broadcast_log_entries \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/sa.json \
  -v "$SA_HOST":/app/keys/sa.json \
  tx-agent:dev
```

## Verify readiness

Go to: [http://localhost:8080/.well-known/agent.json](http://localhost:8080/.well-known/agent.json)

## Run the test

```bash
docker exec -e A2A_BASE_URL="http://localhost:8010" -it txagent python /app/test_a2a.py
```

# Infrastructure (Google)

**tx-agent** runs as a **Cloud Run (Service)** that exposes an HTTP/JSON‑RPC API and publishes its Agent Card at `/.well-known/agent-card.json`. 

## Resource inventory (Project & Region)

* **Project**: `ibc-2025-ai-agents`
* **Runtime region**: `us-central1`

## Artifact Registry (Docker images)

| Repository | Image                                                                   | Purpose                                      |
| ---------- | ----------------------------------------------------------------------- | -------------------------------------------- |
| `tx-agent` | `us-central1-docker.pkg.dev/ibc-2025-ai-agents/tx-agent/tx-agent:<tag>` | Container image for the **tx-agent** service |

## Compute

| Component | Type                  | Name       | Notes                                                                                  |
| --------- | --------------------- | ---------- | -------------------------------------------------------------------------------------- |
| Agent API | Cloud Run **Service** | `tx-agent` | Listens on the `PORT` env var (default `8080`). Serves `/.well-known/agent-card.json`. |

## Identity & Access (Service Account)

| Service Account                                          | Used by                              | Minimum recommended roles                                                                                                     |
| -------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `tx-agent-sa@ibc-2025-ai-agents.iam.gserviceaccount.com` | Runtime for the **tx-agent** service | `roles/datastore.user` (Firestore), `roles/logging.logWriter` (Cloud Logging), `roles/artifactregistry.reader` (pull images). |


## Data

| Service    | Resource                                                               | Purpose                                                              |
| ---------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Firestore  | `projects/ibc-2025-ai-agents/databases/(default)` *(location: `eur3`)* | Data source queried by the agent.                                    |
| Collection | `broadcast_log_entries`                                                | Collection where the stream processor writes and **tx-agent** reads. |

## Configuration (environment variables)

| Variable                    | Typical value                    | Description                                                      |
| --------------------------- | -------------------------------- | ---------------------------------------------------------------- |
| `PORT`                      | `8080`                           | Injected by Cloud Run; the service must listen on this port.     |
| `FIRESTORE_PROJECT_ID`      | `ibc-2025-ai-agents`             | Firestore project ID.                                            |
| `FIRESTORE_DB_COLLECTION`   | `broadcast_log_entries`          | Firestore collection to query.                                   |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` \| `FALSE`                | Choose Vertex AI (`TRUE`) or API‑key mode (`FALSE`).             |
| `VERTEX_LOCATION`           | `us-central1`                    | Vertex AI region (if enabled).                                   |
| `GOOGLE_API_KEY`            | *(required if not using Vertex)* | API key for Google GenAI when `GOOGLE_GENAI_USE_VERTEXAI=FALSE`. |

## Naming conventions

* **Service**: `tx-agent`
* **Artifact Registry (repo)**: `tx-agent`
