#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  create)
    vagrant up Master --provider=virtualbox
    join_token="$(vagrant ssh Master -c \
      'sudo cat /var/lib/rancher/k3s/server/node-token' | tr -d '\r\n')"
    : "${join_token:?Could not read the K3s join token from Master}"
    ORCHESTRATOR_JOIN_TOKEN="$join_token" \
      vagrant up Agent --provider=virtualbox --provision
    unset join_token
    echo 'cluster created'
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
    echo 'Usage: ./orchestrator.sh {create|start|stop}' >&2
    exit 2
    ;;
esac
