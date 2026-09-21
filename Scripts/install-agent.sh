#!/usr/bin/env bash
set -euo pipefail

: "${K3S_TOKEN:?K3S_TOKEN is required to join the cluster}"

curl -sfL https://get.k3s.io |
  INSTALL_K3S_VERSION='v1.36.4+k3s1' \
  K3S_URL='https://192.168.58.10:6443' \
  K3S_TOKEN="$K3S_TOKEN" \
  sh -s - agent --node-ip 192.168.58.11 --flannel-iface eth1
