# Orchestrator Frontend (v2)

This directory contains the v2 frontend for the Broadcast Orchestrator. This is the recommended UI for interacting with the system.

This application is a modern web interface built with React and Vite. It provides a rich user experience for sending requests to the orchestrator agent and visualizing the responses and logs.

## Development Setup

### 1. Install Dependencies

Navigate to this directory and install the required npm packages:

```bash
# From the orchestrator/frontend_v2 directory
npm install
```

### 2. Configure the Backend API

The frontend needs to know the URL of the agent's API. By default, it will try to connect to `http://localhost:8080`. This can be configured via environment variables if your agent is running elsewhere.

### 3. Run the Development Server

To start the local development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` by default (check the console output for the exact URL).

## Building for Production

To create a production-ready build of the application:

```bash
npm run build
```

The optimized static assets will be placed in the `dist` directory.
