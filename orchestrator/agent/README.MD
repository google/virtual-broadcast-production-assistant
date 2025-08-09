# Broadcast Orchestrator Agent

This directory contains the source code for the Broadcast Orchestrator Agent.

The agent is the core backend of the orchestrator system. It is a routing agent responsible for receiving user requests, interpreting them, and delegating tasks to the appropriate specialized agents (e.g., Cuez, EVS, TX). It exposes a REST API that the frontends can interact with.

## Setup and Running Locally

### 1. Create a Virtual Environment (Recommended)

It is recommended to use a Python virtual environment to manage dependencies.

```bash
python -m venv .venv
```

**Activate the environment:**

*   **macOS/Linux:**
    ```bash
    source .venv/bin/activate
    ```
*   **Windows (CMD):**
    ```bash
    .venv\Scripts\activate.bat
    ```
*   **Windows (PowerShell):**
    ```bash
    .venv\Scripts\Activate.ps1
    ```

### 2. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Create Environment Configuration

The agent requires a `.env` file for sensitive configuration, such as API keys and service endpoints.

1.  **Create the `.env` file:**
    ```bash
    cp .env-example .env
    ```

2.  **Populate the `.env` file:**
    You must populate the `.env` file with the correct values for your environment. These secrets (like `GOOGLE_API_KEY`) are not stored in the repository and should be obtained from a secure source, such as Google Cloud Storage or your project's secret manager.

    For local development, you may also need to set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your Firebase service account key file.

### 4. Configure Remote Agents

The agent needs to know the endpoints of the specialized agents it orchestrates. This is configured in the `broadcast_orchestrator/remote_agents_config.yaml` file. Before running the agent, create a copy of the example config and update it with the correct URLs for your remote agent instances.

```bash
# Make sure you are in the orchestrator/agent directory
cp broadcast_orchestrator/remote_agents_config.yaml.example broadcast_orchestrator/remote_agents_config.yaml
```

### 5. Run the Agent Server

The agent is served using `uvicorn`. To run it in development mode with auto-reloading:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`. You can view the auto-generated documentation at `http://localhost:8080/docs`.

## Code Style

This Python code follows the Google Python Style Guide, which includes:
*   Using 2 spaces for indentation (not 4).
*   Adhering to Google's linting rules.

Please ensure your contributions match this style.
