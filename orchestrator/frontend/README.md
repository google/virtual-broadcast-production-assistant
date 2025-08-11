# Orchestrator Frontend (Legacy v1)

This directory contains the legacy v1 frontend for the Broadcast Orchestrator.

> **Note:** This is the older frontend. For new development and the latest features, please use the **[v2 Frontend](../frontend_v2)**.

This UI provides a basic interface for interacting with the Broadcast Orchestrator agent. It allows users to send commands and view responses from the agent.

## Development Setup

### 1. Install Dependencies

Navigate to this directory and install the required npm packages:

```bash
# From the orchestrator/frontend directory
npm install
```

### 2. Run the Development Server

To start the local development server:

```bash
npm run dev
```

The application will typically be available at `http://localhost:3000`. The frontend is configured to connect to the agent's API, which is expected to be running at `http://localhost:8080`.
