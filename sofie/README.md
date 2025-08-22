# Sofie Virtual Production Assistant

This project contains the components for a Virtual Production Assistant for the Sofie TV Production System. It includes the Sofie Agent, which understands natural language commands, and the Sofie Tool, which provides an MCP server for interacting with the Sofie API.

## System Overview

The system is composed of several services that work together:

-   **Sofie Core:** The main Sofie server.
-   **Database:** A MongoDB database for the Sofie Core.
-   **Gateways:** Playout, Live Status, and Package Manager gateways.
-   **Sofie Tool:** An MCP server that exposes the Sofie API as a set of tools.
-   **Sofie Agent:** An agent that uses the Sofie Tool to interact with Sofie based on natural language commands.

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
-   [Node.js](https://nodejs.org/en/) (v22 or higher)
-   [Python](https://www.python.org/downloads/) (v3.11 or higher)

### 1. Environment Configuration

Before running the system, you need to set up the environment variables for the Sofie Agent and Sofie Tool.

#### Sofie Agent

In the `agents/sofie-agent` directory, copy the `.env-example` file to `.env`:

```bash
cp agents/sofie-agent/.env-example agents/sofie-agent/.env
```

Edit the `agents/sofie-agent/.env` file and add your `GOOGLE_API_KEY`.

```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_google_api_key
HOST=http://sofie-tool:3000/mcp
EXTERNAL_HOST=http://localhost:8001
```

#### Sofie Tool

In the `agents/sofie-tool` directory, copy the `.env-example` file to `.env`:

```bash
cp agents/sofie-tool/.env-example agents/sofie-tool/.env
```

Edit the `agents/sofie-tool/.env` file with your Sofie API details:

```
SOFIE_API_BASE=http://core:3000/api/v1.0
SOFIE_LIVE_STATUS_WS=ws://live-status-gateway:8080
SOFIE_API_AUTH_TOKEN=your_sofie_api_token
```

### 2. Running the System with Docker Compose

The easiest way to run the entire system is with Docker Compose. This will start all the necessary Sofie services, the Sofie Tool, and the Sofie Agent.

From the `agents` directory, run:

```bash
docker-compose up --build
```

This will build the Docker images for the `sofie-agent` and `sofie-tool` and start all the services defined in the `docker-compose.yaml` file.

The Sofie Agent will be available at `http://localhost:8001`.

### 3. Running Services Individually (for Development)

If you want to run the Sofie Agent or Sofie Tool individually for development, you can follow these steps.

#### Sofie Tool

1.  Navigate to the `agents/sofie-tool` directory:
    ```bash
    cd agents/sofie-tool
    ```
2.  Install the dependencies:
    ```bash
    npm install
    ```
3.  Run the server in development mode:
    ```bash
    npm run watch
    ```
    This will start the MCP server, and it will automatically restart when you make changes to the source code.

#### Sofie Agent

1.  Navigate to the `agents/sofie-agent` directory:
    ```bash
    cd agents/sofie-agent
    ```
2.  Create a Python virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```
4.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Run the agent:
    ```bash
    adk web
    ```
    This will start the agent's web server.