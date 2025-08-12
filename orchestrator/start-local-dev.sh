#!/bin/bash

# A script to launch the local development environment for the orchestrator.
# It starts the backend agent and the frontend v2 development server.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory of this script to run commands from the correct locations
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Initialize PIDs to null
agent_pid=""
frontend_pid=""

# Function to kill all background processes on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    # The '-' before the PID kills the entire process group.
    # Redirecting stderr to /dev/null to suppress "No such process" errors if they are already stopped.
    if [ -n "$agent_pid" ]; then
        kill -"$agent_pid" 2>/dev/null || true
    fi
    if [ -n "$frontend_pid" ]; then
        kill -"$frontend_pid" 2>/dev/null || true
    fi
    echo "Shutdown complete."
}

# Trap the EXIT signal to run the cleanup function, ensuring shutdown on script exit.
trap cleanup EXIT

# --- Start Backend Agent ---
echo "--- Starting Backend Agent ---"
AGENT_DIR="$SCRIPT_DIR/agent"

if [ ! -f "$AGENT_DIR/venv/bin/uvicorn" ]; then
    echo "Uvicorn not found in agent virtual environment."
    echo "Please ensure you have run 'python3 -m venv venv' and 'pip install -r requirements.txt' in the '$AGENT_DIR' directory."
    exit 1
fi

(   # Run in a subshell to avoid changing the main script's directory
    cd "$AGENT_DIR"
    echo "Launching agent server from '$PWD'..."
    ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 &
)
agent_pid=$!
echo "Agent started with PID: $agent_pid on http://localhost:8080"

# Give the agent a moment to start up
sleep 3

# --- Start Frontend V2 ---
echo "--- Starting Frontend (v2) ---"
FRONTEND_DIR="$SCRIPT_DIR/frontend_v2"

(   # Run in a subshell
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo "node_modules not found in frontend_v2/. Running npm install..."
        npm install
    fi
    echo "Launching frontend dev server from '$PWD'..."
    npm run dev &
)
frontend_pid=$!
echo "Frontend v2 started with PID: $frontend_pid. Access it at http://localhost:5173 (or check console for the correct URL)."


echo ""
echo "-----------------------------------------"
echo "Local development environment is running."
echo "Press Ctrl+C to shut down all services."
echo "-----------------------------------------"

# Wait for any background process to exit. The trap will handle killing the other.
wait -n
