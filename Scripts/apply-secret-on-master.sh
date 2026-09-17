#!/usr/bin/env bash
set -euo pipefail

secret_file=/tmp/orchestrator.env
trap 'rm -f "$secret_file"' EXIT

k3s kubectl wait --for=condition=Ready node --all --timeout=180s
k3s kubectl create secret generic platform-credentials \
  --from-env-file="$secret_file" \
  --dry-run=client -o yaml | k3s kubectl apply -f -
