#!/usr/bin/env bash
# run_test_docker.sh — build image, run server, execute test, cleanup
set -euo pipefail

PORT=8010
IMAGE_TAG="tx-agent:dev"
CONTAINER_NAME="txagent-test"

# Paths (this script sits in tx/tx_agent)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR"
DOCKERFILE="$APP_DIR/Dockerfile"
ENV_FILE="$APP_DIR/.env"

# Optional Service Account JSON (host) -> mounted into container
SA_HOST_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-}"
SA_IN_CONTAINER="/app/keys/sa.json"

echo "[run_test_docker] Building image $IMAGE_TAG with $DOCKERFILE (context: $APP_DIR)"
docker build -t "$IMAGE_TAG" -f "$DOCKERFILE" "$APP_DIR"

# Start container (server)
RUN_ARGS=( --rm -d --name "$CONTAINER_NAME" -p "$PORT:$PORT" -e PORT="$PORT" )

if [[ -f "$ENV_FILE" ]]; then
  echo "[run_test_docker] Using env file: $ENV_FILE"
  RUN_ARGS+=( --env-file "$ENV_FILE" )
fi

if [[ -n "$SA_HOST_PATH" && -f "$SA_HOST_PATH" ]]; then
  echo "[run_test_docker] Mounting SA key: $SA_HOST_PATH -> $SA_IN_CONTAINER"
  RUN_ARGS+=( -v "$SA_HOST_PATH:$SA_IN_CONTAINER:ro" )
  RUN_ARGS+=( -e GOOGLE_APPLICATION_CREDENTIALS="$SA_IN_CONTAINER" )
fi

set -x
docker run "${RUN_ARGS[@]}" "$IMAGE_TAG"
set +x

# Wait for readiness
READY_URL="http://localhost:$PORT/.well-known/agent-card.json"
echo "[run_test_docker] Waiting for $READY_URL"
for i in {1..30}; do
  if curl -sf "$READY_URL" >/dev/null; then
    echo "[run_test_docker] Server is ready."
    break
  fi
  sleep 1
  if [[ $i -eq 30 ]]; then
    echo "[run_test_docker] ERROR: readiness timeout" >&2
    docker logs "$CONTAINER_NAME" || true
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    exit 1
  fi
done


# Extra: wait for readiness inside the container (loopback) to avoid race conditions
echo "[run_test_docker] Verifying readiness inside container..."
set -x
docker exec -it "$CONTAINER_NAME" sh -lc "for i in \$(seq 1 30); do wget -q --spider http://localhost:$PORT/.well-known/agent-card.json && exit 0; sleep 1; done; echo 'inner readiness timeout' >&2; exit 1"
set +x

echo "[run_test_docker] Running test_a2a.py in container..."
set -x
docker exec -e A2A_BASE_URL="http://localhost:$PORT" -it "$CONTAINER_NAME" sh -lc "python /app/test_a2a.py"
EXIT_CODE=$?
set +x

echo "[run_test_docker] Logs (tail)"
docker logs --tail 200 "$CONTAINER_NAME" || true

echo "[run_test_docker] Stopping container..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

exit $EXIT_CODE