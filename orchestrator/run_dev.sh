#!/bin/bash
set -e

# --- Colors ---
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# --- Backend Setup ---
AGENT_VENV_DIR="agent/venv"
if [ ! -d "$AGENT_VENV_DIR" ]; then
    echo "Error: Python virtual environment for the agent not found at '$AGENT_VENV_DIR'."
    echo "Please set up the agent's environment first by following the instructions in 'agent/README.MD'."
    exit 1
fi

# Start the backend in the background using the venv's uvicorn
echo "Starting backend..."
(cd agent && ../"$AGENT_VENV_DIR/bin/uvicorn" broadcast_orchestrator.main:app --reload --port 8080) > backend.log 2>&1 &
BACKEND_PID=$!

LOG_MSG="Backend logs are being written to backend.log. You can view them with 'tail -f backend.log'"
echo -e "${GREEN}${LOG_MSG}${NC}"
read -t 2 -n 1 -s -p "Continuing in 2 seconds... (Press any key to continue immediately)" || true
echo

# --- Frontend Setup ---
# (Assuming npm is installed globally)
echo "Installing frontend dependencies..."
(cd frontend_v2 && npm install)

# --- Process Management ---
# Function to kill the backend process
cleanup() {
    echo
    echo "--- Exiting ---"
    echo "Stopping backend process group (PGID: $BACKEND_PID)..."
    if kill -- -$BACKEND_PID; then
        echo "Backend process group killed."
    else
        echo "Backend process group was not running or could not be killed."
    fi
    echo "Removing log file..."
    rm backend.log
    # Sometimes the process doesn't let go of the port
    kill -9  $(lsof -t -i:8080)
    echo "Force killing any process on port 8080."
    echo "Cleanup complete."
    sleep 1
}



# Trap exit signals
trap cleanup EXIT SIGINT SIGTERM

# --- Start Frontend ---
echo "Starting frontend..."
(cd frontend_v2 && npm run dev)
