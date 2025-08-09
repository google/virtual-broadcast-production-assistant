# Broadcast Orchestrator

Welcome to the Broadcast Orchestrator directory. This project is a multi-agent system designed to streamline broadcast operations by orchestrating various specialized agents.

This README provides a central guide for setting up and running the different components of the system locally.

## Project Structure

The orchestrator is composed of a central **agent** and multiple **frontends** for interaction:

*   **`agent/`**: The core of the system. This is a Python-based routing agent that receives user requests, interprets their intent, and delegates tasks to the appropriate downstream agents (e.g., Cuez, EVS, TX). For more details, see the [Agent README](./agent/README.MD).
*   **`frontend_v2/`**: The recommended web interface for interacting with the orchestrator. It is a modern React application that provides a rich user experience. For more details, see the [Frontend v2 README](./frontend_v2/README.md).
*   **`frontend/`**: A legacy web interface. This is the original UI and is kept for reference. For new development, please use `frontend_v2`. For more details, see the [Legacy Frontend README](./frontend/README.md).
*   **`app.py`**: A simple, all-in-one Gradio application that runs both the agent and a basic UI in a single process. This is useful for quick tests and demonstrations.

## Quick Start: Running the Agent and v2 Frontend

This is the recommended setup for local development. You will need to open two separate terminal windows.

### Terminal 1: Run the Agent

1.  **Navigate to the agent directory:**
    ```bash
    cd orchestrator/agent
    ```

2.  **Set up the Python environment and install dependencies** (if you haven't already):
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure the remote agents:**
    ```bash
    cp broadcast_orchestrator/remote_agents_config.yaml.example broadcast_orchestrator/remote_agents_config.yaml
    ```
    *Update `remote_agents_config.yaml` with the correct endpoints for your downstream agents.*

4.  **Start the agent server:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
    ```
    *The agent API will now be running at `http://localhost:8080`.*

### Terminal 2: Run the Frontend (v2)

1.  **Navigate to the v2 frontend directory:**
    ```bash
    cd orchestrator/frontend_v2
    ```

2.  **Install dependencies** (if you haven't already):
    ```bash
    npm install
    ```

3.  **Start the development server:**
    ```bash
    npm run dev
    ```
    *The frontend will now be running at `http://localhost:5173` (or another port if 5173 is busy).*

You can now open your browser to the frontend address and start using the orchestrator.

## Alternative Setups

### Running with the Legacy Frontend

If you need to use the legacy UI, follow the "Quick Start" instructions but in Terminal 2, navigate to `orchestrator/frontend` and run `npm run dev`. The legacy frontend will be available at `http://localhost:3000`.

### Running the Simple Gradio UI

For a quick, all-in-one setup, you can use the `app.py` script. This runs the agent and a simple UI in one process.

1.  **Navigate to the orchestrator directory:**
    ```bash
    cd orchestrator
    ```

2.  **Set up the Python environment and install dependencies** (this uses the same `requirements.txt` as the agent):
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r agent/requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```
    *The Gradio UI will be available at `http://localhost:8083`.*
