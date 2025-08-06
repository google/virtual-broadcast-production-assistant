#!/bin/bash

# This script deploys the agent to Google Cloud Run directly from source.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Prerequisites ---
# 1. Google Cloud SDK (gcloud) is installed.
# 2. You are authenticated: `gcloud auth login`
# 3. Your project is set: `gcloud config set project YOUR_PROJECT_ID`
# 4. The required APIs are enabled: `gcloud services enable run.googleapis.com cloudbuild.googleapis.com`

# --- Configuration ---

# Load environment variables from .env file to get project, region, etc.
if [ -f .env ]; then
  # `set -a` ensures that all variables defined in the .env file are
  # exported to the environment of the script.
  set -a
  source .env
  set +a
else
  echo "Error: .env file not found. Please create one with your configuration."
  exit 1
fi

# Variables are sourced from your .env file
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION}"
SERVICE_NAME="${APP_NAME}"

# --- Script ---

echo "--- Deploying to Cloud Run from Source ---"
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "------------------------------------------"

# Convert the .env file to a comma-separated string for gcloud
# This reads the .env file, removes comments and empty lines,
# and joins the lines with a comma.
ENV_VARS_STRING=$(grep -v '^#' .env | grep -v '^$' | tr '\n' ',' | sed 's/,$//')

# Deploy to Cloud Run from source.
# This command uses Google Cloud Build to build the image from the Dockerfile
# and then deploys it to Cloud Run. No local Docker installation is required.
echo "STEP 1: Submitting source for build and deployment..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --platform managed \
  --region "${REGION}" \
  --set-env-vars="${ENV_VARS_STRING}" \
  --cpu=2 \
  --memory=2Gi \
  --session-affinity \
  --service-account="websocket-service-account@peerless-kit-450316-g1.iam.gserviceaccount.com" \
  --allow-unauthenticated

echo "--- Deployment Complete ---"
echo "Service URL:"
gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)'
