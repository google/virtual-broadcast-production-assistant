# Agent Health Checker

This document provides a comprehensive overview of the Agent Health Checker service, including its purpose, architecture, configuration, and deployment process.

## 1. Project Overview

The Agent Health Checker is a service designed to run as a [Google Cloud Run Job](https://cloud.google.com/run/docs/jobs). Its primary responsibility is to periodically check the health status of a list of remote agents. It then records the latest status of each agent in a Google Firestore database, providing a near real-time look at the health of the entire agent fleet.

## 2. How it Works

The health checking process is orchestrated by the `main.py` script and follows these steps:

1.  **Initialization**: The Cloud Run Job starts, which executes the Python script.
2.  **Fetch Agent List**: The service queries the `agent_status` collection in Firestore to get a list of all registered agents.
3.  **Concurrent Health Checks**: Using Python's `asyncio` library, the service runs health checks for all agents concurrently to ensure efficiency.
4.  **Individual Health Check**: For each agent, the service performs the following actions:
    *   **API Key Retrieval**: If an agent requires an API key for authentication, it fetches the key from [Google Secret Manager](https://cloud.google.com/secret-manager).
    *   **Agent Card Discovery**: It fetches the agent's `agent.json` file from its `/.well-known/agent.json` endpoint. This file contains metadata about the agent, including its capabilities and the correct A2A (Agent-to-Agent) communication endpoint.
    *   **A2A Health Check**: It sends a simple "Are you there?" message to the agent's A2A endpoint using the `a2a-sdk`.
    *   **Status Determination**: Based on the success or failure of the A2A message, the agent's status is marked as `online` or `offline`. If any errors occur during the process (e.g., failed to fetch a secret), the status is marked as `error`.
5.  **Update Firestore**: The service updates each agent's document in the `agent_status` collection with the new status, a `last_checked` timestamp, and the content of its `agent.json` card.

## 3. Configuration

To run the Agent Health Checker, you need to configure the following: a Firestore database and, optionally, Secret Manager.

### 3.1. Firestore Setup

The service requires a Firestore collection named `agent_status`. Each document in this collection represents an agent to be monitored and stores both its configuration and its latest health status. The document ID should be a unique identifier for the agent.

#### **Input Fields**

These fields must be present in the document for the health checker to work correctly:

*   `url` (String): The base URL of the remote agent. The health checker will look for the agent card at `{url}/.well-known/agent.json`.
*   `name` (String): A human-readable name for the agent.
*   `api_key_secret` (String, Optional): The name of the secret in Google Secret Manager that stores the agent's API key. If the agent does not require an API key, this field can be omitted.

#### **Output Fields**

These fields are added or updated by the health checker script:

*   `status` (String): The health status of the agent. Can be `online`, `offline`, or `error`.
*   `last_checked` (Timestamp): The timestamp of the last health check.
*   `card` (Map): The content of the agent's `agent.json` file.
*   `a2a_endpoint` (String): The Agent-to-Agent communication endpoint discovered from the agent card.

#### **Example Document**

Below is an example of what a document in the `agent_status` collection would look like after a successful health check.

```json
// Document ID: my-cool-agent
{
  "name": "My Cool Agent",
  "url": "https://my-agent.example.com",
  "api_key_secret": "my-cool-agent-api-key",
  "status": "online",
  "last_checked": "2025-08-30T12:00:00Z",
  "card": {
    "name": "My Cool Agent",
    "url": "https://my-agent.example.com/a2a",
    "description": "An example agent card."
  },
  "a2a_endpoint": "https://my-agent.example.com/a2a"
}
```

### 3.2. Secret Manager Setup

If you are using the `api_key_secret` field, you must create a corresponding secret in [Google Secret Manager](https://cloud.google.com/secret-manager).

The service account that executes the Cloud Run Job must be granted the **Secret Manager Secret Accessor** (`roles/secretmanager.secretAccessor`) IAM role to be able to retrieve these secrets.

## 4. Local Development

You can run the health checker locally for development and testing purposes.

### 4.1. Prerequisites

*   Python 3.11 or later
*   [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured

### 4.2. Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd orchestrator/agent-health-checker
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The `requirements.txt` file contains all dependencies needed for local development, including testing and linting tools.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Authenticate with Google Cloud:**
    To access Firestore and Secret Manager from your local machine, you need to authenticate.
    ```bash
    gcloud auth application-default login
    ```

### 4.3. Running Tests

The project uses `pytest` for unit testing. To run the tests, execute the following command:
```bash
pytest
```

### 4.4. Linting

The project uses `pylint` to enforce code style. To check your code, run:
```bash
pylint --rcfile=.pylintrc main.py test_main.py
```

## 5. Deployment

This service is designed to be deployed as a Docker container to [Google Cloud Run](https://cloud.google.com/run). The repository includes a `cloudbuild.yaml` file that automates the build and deployment process.

### 5.1. Build and Push

The `cloudbuild.yaml` file defines a [Cloud Build](https://cloud.google.com/build) pipeline that:

1.  Installs dependencies.
2.  Runs linting checks with `pylint`.
3.  Runs unit tests with `pytest`.
4.  Builds the Docker image using the provided `Dockerfile`.
5.  Pushes the image to [Google Artifact Registry](https://cloud.google.com/artifact-registry).

You can trigger this pipeline by connecting it to your source code repository (e.g., GitHub, Bitbucket).

### 5.2. Deploy to Cloud Run

Once the Docker image is available in Artifact Registry, you can deploy it as a [Cloud Run Job](https://cloud.google.com/run/docs/jobs).

You will need to configure the job with the appropriate service account that has access to Firestore and Secret Manager.

It is recommended to use a [Cloud Scheduler](https://cloud.google.com/scheduler) job to trigger the Cloud Run Job on a regular schedule (e.g., every 15 minutes).
