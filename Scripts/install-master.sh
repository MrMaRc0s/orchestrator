#!/usr/bin/env bash
set -euo pipefail

curl -sfL https://get.k3s.io |
  INSTALL_K3S_VERSION='v1.36.4+k3s1' sh -s - server \
    --node-ip 192.168.58.10 \
    --advertise-address 192.168.58.10
