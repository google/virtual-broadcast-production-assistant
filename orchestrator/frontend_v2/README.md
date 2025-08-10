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

### 2. Create Environment Configuration

The frontend requires a `.env.local` file for configuration, including Firebase credentials.

1.  **Create the file:**
    ```bash
    touch .env.local
    ```

2.  **Populate the file:**
    Add the following environment variables to the file. The values for your Firebase project can be found in the Firebase console. These secrets should be sourced securely and not be committed to the repository.

    ```
    VITE_FIREBASE_API_KEY="YOUR_API_KEY"
    VITE_FIREBASE_AUTH_DOMAIN="YOUR_AUTH_DOMAIN"
    VITE_FIREBASE_PROJECT_ID="YOUR_PROJECT_ID"
    VITE_FIREBASE_STORAGE_BUCKET="YOUR_STORAGE_BUCKET"
    VITE_FIREBASE_MESSAGING_SENDER_ID="YOUR_MESSAGING_SENDER_ID"
    VITE_FIREBASE_APP_ID="YOUR_APP_ID"
    ```

### 3. Configure the Backend API

The frontend needs to know the URL of the agent's API. By default, it will try to connect to `http://localhost:8080`. This can be configured via an environment variable if your agent is running elsewhere. You can add this to your `.env.local` file:

```
VITE_WEBSOCKET_URL="http://localhost:8080"
```

### 4. Run the Development Server

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
