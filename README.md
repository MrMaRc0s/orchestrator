# Orchestrator

A two-node K3s cluster, built with Vagrant/VirtualBox, running a small
movies-and-billing application: a Flask API gateway in front of an
inventory service (PostgreSQL-backed) and an async billing consumer
(RabbitMQ + PostgreSQL).

This is the 01-edu "Orchestrator" project. The application services reuse
[Play With Containers](https://platform.zone01.gr/git/cgkaldan/play-with-containers).

## Architecture

```
                     external :3000
                          |
                  api-gateway-app (Deployment + HPA)
                     /                \
        /api/movies[/id]          POST /api/billing
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
still leaves `POST /api/billing/` returning `200`; only the write into Postgres
is delayed until the consumer is scaled back up.

| Component | Kind | Notes |
| --- | --- | --- |
| `inventory-app` | Deployment + HPA | Flask + SQLAlchemy/psycopg, port `8080`, CPU target 60% (1-3 replicas) |
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

Both VMs have a NAT interface and a private `192.168.58.0/24` interface.
The K3s install scripts pin Flannel to `eth1` (the private interface), so
cross-node Pod traffic does not use VirtualBox's duplicate NAT address.

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
- Docker and a Docker Hub account to build and publish the six images

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

Build and push the images from the repository root before creating the cluster.
The three restored application images use tag `1.1`; the database and RabbitMQ
images use tag `1.0`. Authenticate with `docker login` first:

```sh
for service in inventory-database billing-database rabbit-queue; do
  docker build -t "cgkaldan/$service:1.0" "srcs/$service"
  docker push "cgkaldan/$service:1.0"
done
for service in inventory-app billing-app api-gateway-app; do
  docker build -t "cgkaldan/$service:1.1" "srcs/$service"
  docker push "cgkaldan/$service:1.1"
done
```

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

For an existing Master VM, run `vagrant reload Master` after changing its
forwarded ports in the Vagrantfile. This project forwards the Kubernetes API
to host `127.0.0.1:16443` and the Gateway to host `127.0.0.1:3000`.

To configure host-side `kubectl`, copy the cluster config to the ignored
`kubeconfig` file and point it at the forwarded API port:

```sh
vagrant ssh Master -c 'sudo cat /etc/rancher/k3s/k3s.yaml' > kubeconfig
sed -i 's#https://127.0.0.1:6443#https://127.0.0.1:16443#' kubeconfig
chmod 600 kubeconfig
export KUBECONFIG="$PWD/kubeconfig"
```

If Vagrant runs on another computer, keep an SSH tunnel from your laptop to
that computer open for Postman and host-side `kubectl`:

```sh
ssh -N -L 16443:127.0.0.1:16443 -L 3000:127.0.0.1:3000 USER@REMOTE_HOST
```

Use a local copy of `kubeconfig` on the laptop with the same API URL. Only
the Gateway is forwarded to Postman; databases and RabbitMQ remain internal.

## Verifying the cluster

```sh
kubectl get nodes                       # two Ready nodes: k3s-master, k3s-agent
kubectl get pods,svc,hpa,pvc
kubectl top pods                        # metrics-server must report real CPU, not <unknown>
```

Once `api-gateway-app`'s `LoadBalancer` Service is up, exercise the audit
endpoints from the Vagrant host or through the laptop SSH tunnel:

```sh
curl -i -X POST http://127.0.0.1:3000/api/movies/ -H 'Content-Type: application/json' \
  -d '{"title":"A new movie","description":"Very short description"}'
curl -i http://127.0.0.1:3000/api/movies/

curl -i -X POST http://127.0.0.1:3000/api/billing/ -H 'Content-Type: application/json' \
  -d '{"user_id":"20","number_of_items":"99","total_amount":"250"}'
```

To confirm billing is decoupled from `billing-app`, scale it to `0`, send
another `POST /api/billing/` with `user_id` `22` (still `200`), and query the
database before and after scaling back to `1`:

```sh
kubectl scale statefulset billing-app --replicas=0
curl -i -X POST http://127.0.0.1:3000/api/billing/ -H 'Content-Type: application/json' \
  -d '{"user_id":"22","number_of_items":"10","total_amount":"50"}'
kubectl exec billing-db-0 -- psql -U postgres -d orders -c 'TABLE orders;'
kubectl scale statefulset billing-app --replicas=1
kubectl rollout status statefulset/billing-app
kubectl exec billing-db-0 -- psql -U postgres -d orders -c 'TABLE orders;'
```

## Notes

- Namespace is `default` throughout, since the audit inspects resources
  with `kubectl get all` (no `-n` flag).
- Manifests use public, versioned images under `docker.io/cgkaldan/`; no
  `latest` tag is used.
