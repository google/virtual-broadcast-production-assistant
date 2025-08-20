
# Gemini Code Assistant Documentation

This document provides an overview of the Broadcast Orchestrator Agent project for the Gemini Code Assistant.

## Project Overview

The Broadcast Orchestrator Agent is the central backend component of a virtual production assistant. It functions as a routing agent, receiving user requests through a WebSocket-based API, interpreting them using Google's Gemini AI model, and delegating the tasks to appropriate specialized agents (e.g., Cuez, EVS, TX). The agent is built with Python using the FastAPI framework and leverages the Google Agent Development Kit (ADK) for its core logic.

The system is designed to be multi-tenant, with user-specific preferences stored in Firestore. It dynamically loads and communicates with remote agents based on user settings and the nature of the request.

## Key Technologies

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI/LLM**: [Google Gemini](https://deepmind.google/technologies/gemini/)
- **Agent Framework**: [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- **Real-time Communication**: WebSockets
- **Cloud Services**:
    - [Google Cloud Firestore](https://firebase.google.com/docs/firestore): For storing user preferences and agent status.
    - [Google Cloud Secret Manager](https://cloud.google.com/secret-manager): For managing API keys and other secrets.
- **Authentication**: [Firebase Authentication](https://firebase.google.com/docs/auth) (JWT-based)
- **Configuration**: YAML for remote agent configuration, `.env` for environment variables.

## Commands

Here are some common commands for working with this project.

### Setup

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### Running the Application

**Run the development server:**
```bash
uvicorn broadcast_orchestrator.main:app --host 0.0.0.0 --port 8080 --reload
```
The API will be available at `http://localhost:8080`, and the OpenAPI documentation can be accessed at `http://localhost:8080/docs`.

### Testing and Linting

There are no tests as yet

**Run Pylint:**
```bash
pylint broadcast_orchestrator/
```

## File Structure

Here is a brief overview of the key files and directories in the project:

-   `broadcast_orchestrator/`: The main Python package for the agent.
    -   `main.py`: The FastAPI application entry point. It handles WebSocket connections, authentication, and initializes the agent.
    -   `agent.py`: Contains the core logic for the `RoutingAgent`. This includes initializing the ADK agent, managing remote agent connections, and processing user requests.
    -   `remote_agents_config.yaml`: Configuration file for defining the remote agents that the orchestrator can connect to.
    -   `system_instructions.txt`: The base system prompt/instructions for the Gemini model.
    -   `automation_system_instructions.py`: Contains specialized instructions and configurations for different automation systems (e.g., Cuez, Sofie).
-   `requirements.txt`: A list of all the Python dependencies for the project.
-   `Dockerfile`: For building the Docker container image of the application.
-   `cloudbuild.yaml`: Configuration for Google Cloud Build, for continuous integration and deployment.
-   `.pylintrc`: Configuration file for the Pylint linter.
-   `README.MD`: The general project README file with setup and usage instructions.

## Persona

You are an expert Software Engine with Cloud engineering experiance. You should know and understand Google's Agent Developer Kit SDK and the
A2A protocal sdk.
