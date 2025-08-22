# Stream-Processor component

## Test locally (Build)
```bash
docker build -t stream-processor:dev -f stream-processor/Dockerfile stream-processor
```

## Test processing

```bash
SA="$HOME/.keys/google/some-credentials.json"

docker run --rm --name spdev -it \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/sa.json \
  -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  -e GOOGLE_API_KEY=<YOUR API KEY> \
  -e FIRESTORE_DB_COLLECTION=broadcast_log_entries \
  -e STREAM_SSL_VERIFY=FALSE \
  -v "$SA":/app/keys/sa.json:ro \
  stream-processor:dev \
  --stream-url "https://some-domain.com/stream.m3u8"
```


# Infrastructure

**stream-processor** runs as a **Cloud Run Job**. Each execution pulls an HLS stream and emits structured entries to Firestore. The container’s entrypoint runs the worker directly (no HTTP server):

* **ENTRYPOINT**: `python /app/main.py`
* **Args at execution time**: `--stream-url=<HLS_URL>`

## Resource inventory (Project & Region)

* **Project**: `ibc-2025-ai-agents`
* **Runtime region**: `us-central1`
* **Firestore DB**: `(default)` in location `eur3`

## Artifact Registry (Docker images)

| Repository                  | Image                                                                                                     | Purpose                                   |
| --------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `tx-agent-stream-processor` | `us-central1-docker.pkg.dev/ibc-2025-ai-agents/tx-agent-stream-processor/tx-agent-stream-processor:<tag>` | Container image for the **Cloud Run Job** |

## Compute

| Component        | Type              | Name                        | Key settings                                                                                                                        |
| ---------------- | ----------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Stream processor | Cloud Run **Job** | `tx-agent-stream-processor` | `tasks=1`, `task-timeout=21600s` (6h), typical resources `--cpu=1 --memory=1Gi`. The job is invoked with `--args="--stream-url=…"`. |

## Identity & Access (Service Accounts)

| Service Account                                          | Used by                                                     | Minimum recommended roles                                                                                                           |
| -------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `tx-agent-sa@ibc-2025-ai-agents.iam.gserviceaccount.com` | **Runtime SA of the Job**                                   | `roles/artifactregistry.reader` (pull image), `roles/logging.logWriter` (Cloud Logging), `roles/datastore.user` (Firestore access). |


## Data

| Service    | Resource                                                               | Purpose                                      |
| ---------- | ---------------------------------------------------------------------- | -------------------------------------------- |
| Firestore  | `projects/ibc-2025-ai-agents/databases/(default)` *(location: `eur3`)* | Target database for persisted entries.       |
| Collection | `broadcast_log_entries`                                                | Destination collection for produced records. |

## Configuration (environment variables)

| Variable                    | Typical value                    | Description                                                                  |
| --------------------------- | -------------------------------- | ---------------------------------------------------------------------------- |
| `FIRESTORE_PROJECT_ID`      | `ibc-2025-ai-agents`             | Firestore project ID used by the worker.                                     |
| `FIRESTORE_DB_COLLECTION`   | `broadcast_log_entries`          | Firestore collection for writes.                                             |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` \| `FALSE`                | Choose Vertex AI (`TRUE`) or API‑key mode (`FALSE`).                         |
| `VERTEX_LOCATION`           | `us-central1`                    | Vertex AI region (if enabled).                                               |
| `GOOGLE_API_KEY`            | *(required if not using Vertex)* | API key for Google GenAI when `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.             |
| `STREAM_SSL_VERIFY`         | `true` \| `false`                | Optional switch to relax TLS verification for playlist fetch (testing only). |

## Naming conventions

* **Job**: `tx-agent-stream-processor`
* **Artifact Registry (repo)**: `tx-agent-stream-processor`

