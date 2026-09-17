#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nfs-kernel-server nfs-common

mkdir -p /srv/orchestrator/nfs/inventory-database
mkdir -p /srv/orchestrator/nfs/billing-database
mkdir -p /etc/exports.d

cat > /etc/exports.d/orchestrator.exports <<'EXPORTS'
/srv/orchestrator/nfs/inventory-database 192.168.58.0/24(rw,sync,no_subtree_check,no_root_squash)
/srv/orchestrator/nfs/billing-database 192.168.58.0/24(rw,sync,no_subtree_check,no_root_squash)
EXPORTS

systemctl enable --now nfs-kernel-server
exportfs -ra
