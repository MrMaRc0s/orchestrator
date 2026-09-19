# Orchestrator

A two-node K3s cluster, built with Vagrant/VirtualBox, running a small
movies-and-billing application: a Flask API gateway in front of an
inventory service (PostgreSQL-backed) and an async billing consumer
(RabbitMQ + PostgreSQL).

This is the 01-edu "Orchestrator" project. Source services are adapted from
[Play With Containers](https://platform.zone01.gr/git/cgkaldan/play-with-containers).

## Architecture

```
                     external :3000
                          |
                  api-gateway-app (Deployment + HPA)
                     /                \
        GET/POST /movies          POST /billing
                 |                      |
       inventory-app (Deployment + HPA)  rabbit-queue (billing_queue)
                 |                      |
       inventory-database          billing-app (StatefulSet, 1 replica)
       (StatefulSet, PVC)               |
                                   billing-database
                                   (StatefulSet, PVC)
```

The gateway publishes billing requests straight onto RabbitMQ instead of
calling `billing-app` directly. That way scaling `billing-app` to `0`
still leaves `POST /billing` returning `200`; only the write into Postgres
is delayed until the consumer is scaled back up.

| Component | Kind | Notes |
| --- | --- | --- |
| `inventory-app` | Deployment + HPA | Flask + psycopg2, port `8080`, CPU target 60% (1-3 replicas) |
| `api-gateway-app` | Deployment + HPA | Flask, port `3000`, exposed via a `LoadBalancer` Service, CPU target 60% (1-3 replicas) |
| `billing-app` | StatefulSet (1 replica) | pika consumer, no HTTP port, reads `billing_queue` |
| `inventory-database` | StatefulSet (1 replica) | PostgreSQL, DB `movies_db` |
| `billing-database` | StatefulSet (1 replica) | PostgreSQL, DB `orders` |
| `rabbit-queue` | Deployment | RabbitMQ, queue `billing_queue` |

Cross-node storage for the two database PVCs is provided by an NFS export
from the Master VM, mounted from both nodes — this keeps the school-project
requirement that a database pod can be rescheduled onto the other node
without losing data. The Master remains a storage single point of failure;
K3s's default `local-path` storage class is intentionally not used for the
database claims.

## Repository layout

```
Vagrantfile              # Master + Agent VM definitions (VirtualBox, private network)
orchestrator.sh          # create / apply / start / stop entrypoint
Scripts/                 # K3s install, NFS storage, secret provisioning
Manifests/platform/      # Databases, RabbitMQ, storage (Secret-backed)
Manifests/apps/          # Deployments/StatefulSet/Services/HPAs for the three apps
srcs/<service>/          # Dockerfile + source for each of the six images
```

## Prerequisites

- Vagrant + VirtualBox
- `kubectl` on the host (or use `vagrant ssh Master -c 'sudo k3s kubectl ...'`)

## Setup

Copy the credentials template and fill in real passwords (never commit
`.env`):

```sh
cp .env.example .env
```

`.env` must define:

```
INVENTORY_DB_NAME, INVENTORY_DB_USER, INVENTORY_DB_PASSWORD
BILLING_DB_NAME, BILLING_DB_USER, BILLING_DB_PASSWORD
RABBITMQ_USER, RABBITMQ_PASSWORD
```

These are applied as a single `platform-credentials` Kubernetes Secret and
consumed by every workload via `secretKeyRef` — no plaintext credentials
ever appear in a tracked manifest.

## Usage

```sh
./orchestrator.sh create   # boot Master + Agent, join the cluster, apply all manifests
./orchestrator.sh apply    # re-apply the Secret and Manifests/platform + Manifests/apps
./orchestrator.sh start    # vagrant up both VMs (no re-provisioning)
./orchestrator.sh stop     # vagrant halt both VMs; VM disks and data are preserved
```

`create` boots the Master, reads its K3s join token, boots the Agent with
that token, then runs `apply`. `apply` uploads `.env` and applies every
manifest under `Manifests/platform/` (storage → service → statefulset) and
`Manifests/apps/` (deployment → service → hpa/statefulset), in a glob order
chosen so dependencies land before the things that need them.

## Verifying the cluster

```sh
kubectl get nodes                       # two Ready nodes: k3s-master, k3s-agent
kubectl get pods,svc,hpa,pvc
kubectl top pods                        # metrics-server must report real CPU, not <unknown>
```

Once `api-gateway-app`'s `LoadBalancer` Service is up (K3s ServiceLB binds
`:3000` on every node's host network), exercise it from the host:

```sh
curl -X POST http://192.168.58.10:3000/movies -H 'Content-Type: application/json' \
  -d '{"title":"Arrival"}'
curl http://192.168.58.10:3000/movies

curl -X POST http://192.168.58.10:3000/billing -H 'Content-Type: application/json' \
  -d '{"item":"popcorn"}'
```

To confirm billing is decoupled from `billing-app`, scale it to `0`, repeat
the `POST /billing` call (still `200`, order not yet in Postgres), then
scale back to `1` and confirm the order appears:

```sh
kubectl scale statefulset billing-app --replicas=0
kubectl scale statefulset billing-app --replicas=1
```

## Notes

- Namespace is `default` throughout, since the audit inspects resources
  with `kubectl get all` (no `-n` flag).
- Images are published as versioned public tags under
  `docker.io/cgkaldan/<service>:1.0` — no `latest` tag is referenced by any
  manifest.
