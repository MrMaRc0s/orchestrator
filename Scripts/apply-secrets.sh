#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-.env}"
if [ ! -f "$env_file" ]; then
  echo "Missing $env_file; copy .env.example to .env and set a password" >&2
  exit 1
fi

for key in INVENTORY_DB_NAME INVENTORY_DB_USER INVENTORY_DB_PASSWORD; do
  if ! grep -Eq "^${key}=.+$" "$env_file"; then
    echo "Missing or empty $key in $env_file" >&2
    exit 1
  fi
done

kubectl create secret generic platform-credentials \
  --from-env-file="$env_file" \
  --dry-run=client -o yaml | kubectl apply -f -
