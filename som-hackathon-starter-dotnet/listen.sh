#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env.local ]]; then
  echo "ERROR: .env.local not found at $(pwd)/.env.local"
  echo "Run: cp .env.local.example .env.local  then set Kafka__SaslUsername to your GCP email."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.local
set +a

: "${Kafka__BootstrapServers:?Kafka__BootstrapServers not set in .env.local}"
: "${Kafka__SaslUsername:?Kafka__SaslUsername not set in .env.local (must be your GCP email)}"

export Kafka__SecurityProtocol="${Kafka__SecurityProtocol:-SaslSsl}"
export ASPNETCORE_ENVIRONMENT="${ASPNETCORE_ENVIRONMENT:-Production}"

echo "==> Pre-flight 1/4: Tailscale running?"
if ! command -v tailscale >/dev/null 2>&1; then
  echo "FAILED. Tailscale not installed. https://tailscale.com — log in to the project tailnet, toggle 'Use Subnet Routes' ON."
  exit 2
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "FAILED. Tailscale not running / not logged in. Open Tailscale app, sign in, ensure 'Use Subnet Routes' is ON."
  exit 2
fi

echo "==> Pre-flight 2/4: gcloud ADC set up?"
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo "FAILED. Run:  gcloud auth login  &&  gcloud auth application-default login"
  exit 2
fi

echo "==> Pre-flight 3/4: TCP reach to broker via Tailscale?"
host="${Kafka__BootstrapServers%%:*}"
port="${Kafka__BootstrapServers##*:}"
if ! nc -vz -G 5 "$host" "$port" 2>&1; then
  echo "FAILED. Cannot reach ${host}:${port}. VPC route advertised? Check Tailscale admin console: route 10.0.0.0/24 enabled on som-tailscale-router."
  exit 2
fi

echo "==> Pre-flight 4/4: minting fresh OAuth access token for Kafka SASL/PLAIN password..."
Kafka__SaslPassword="$(gcloud auth application-default print-access-token)"
export Kafka__SaslPassword
echo "    token length: ${#Kafka__SaslPassword} chars"

echo "==> All pre-flight green. Starting dotnet ..."
echo "    user:   $Kafka__SaslUsername"
echo "    broker: $Kafka__BootstrapServers"
exec dotnet run
