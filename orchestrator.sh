#!/usr/bin/env bash
set -euo pipefail

require_env() {
  if [ ! -f .env ]; then
    echo 'Missing .env; copy .env.example and fill in the passwords' >&2
    exit 1
  fi
  for key in INVENTORY_DB_NAME INVENTORY_DB_USER INVENTORY_DB_PASSWORD \
    BILLING_DB_NAME BILLING_DB_USER BILLING_DB_PASSWORD \
    RABBITMQ_USER RABBITMQ_PASSWORD; do
    if ! grep -Eq "^${key}=.+$" .env; then
      echo "Missing or empty $key in .env" >&2
      exit 1
    fi
  done
}

apply_platform() {
  vagrant upload .env /tmp/orchestrator.env Master
  vagrant upload Scripts/apply-secret-on-master.sh /tmp/apply-secret-on-master.sh Master
  vagrant ssh Master -c 'sudo bash /tmp/apply-secret-on-master.sh'

  for pattern in '*-storage.yaml' '*-service.yaml' '*-statefulset.yaml' '*-deployment.yaml'; do
    for manifest in Manifests/platform/$pattern; do
      [ -f "$manifest" ] || continue
      destination="/tmp/$(basename "$manifest")"
      vagrant upload "$manifest" "$destination" Master
      vagrant ssh Master -c "sudo k3s kubectl apply -f $destination"
    done
  done
}

case "${1:-}" in
  create)
    require_env
    vagrant up Master --provider=virtualbox
    join_token="$(vagrant ssh Master -c \
      'sudo cat /var/lib/rancher/k3s/server/node-token' | tr -d '\r\n')"
    : "${join_token:?Could not read the K3s join token from Master}"
    ORCHESTRATOR_JOIN_TOKEN="$join_token" \
      vagrant up Agent --provider=virtualbox --provision
    unset join_token

    apply_platform
    echo 'cluster created'
    ;;
  apply)
    require_env
    apply_platform
    echo 'platform applied'
    ;;
  start)
    vagrant up Master --provider=virtualbox
    vagrant up Agent --provider=virtualbox
    echo 'cluster started'
    ;;
  stop)
    vagrant halt
    echo 'cluster stopped'
    ;;
  *)
    echo 'Usage: ./orchestrator.sh {create|apply|start|stop}' >&2
    exit 2
    ;;
esac
