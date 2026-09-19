# Developer B working notes — images and application delivery

## Images

Three images, same Docker Hub namespace and tag scheme A already used for the
platform images (`docker.io/cgkaldan/<service>:1.0`):

- `inventory-app` — Flask + psycopg2 on `debian:12-slim`, port `8080`.
  `GET/POST /movies`, `GET /healthz`. Creates the `movies` table itself on
  first boot against `movies_db`.
- `billing-app` — pika consumer, no HTTP port. Reads `billing_queue`, writes
  into the `orders` table on `billing-database`.
- `api-gateway-app` — Flask, port `3000`. Proxies `/movies` to `inventory-app`
  over cluster DNS, and publishes `/billing` straight onto `billing_queue`.

Packages come from apt (`python3-flask`, `python3-psycopg2`, `python3-pika`,
`python3-requests`) instead of pip, matching the DB/queue Dockerfiles A
already wrote — no extra package manager, no `requirements.txt`.

## Why billing is decoupled from billing-app

The audit step scales `billing-app` to 0 and expects a Billing POST to still
return 200 with the order missing from Postgres, then reappearing once
scaled back to 1. If the gateway forwarded billing requests to `billing-app`
directly, that pod being down would break the request instead. So the
gateway talks to RabbitMQ directly and only `billing-app` (the consumer)
talks to Postgres — `billing_queue` is the thing that has to stay up, not
the consumer pod.

## Gateway exposure

Went with a `LoadBalancer` Service for `api-gateway-app` rather than
hostPort/nodeSelector pinning or an Ingress. K3s ships its own ServiceLB
(Klipper) that binds the Service port on every node's host network for
`LoadBalancer` type Services with no extra manifest work, so `:3000` should
be reachable on both the Master and Agent private IPs.

**Depends on A**: this only works if ServiceLB hasn't been turned off with
`--disable=servicelb` on the K3s server. Need to confirm with A once the
Vagrant boxes are up — if it's disabled, we'll switch to a NodePort or ask A
to re-enable it, but that's their file to change, not mine.

Checked whether an Ingress makes sense here too: it doesn't, since there's
only one path we want exposed and it's supposed to be reached directly on
its container port for the audit, not fronted by another routing layer.

## Testing done so far (no cluster available yet)

- `python3 -m py_compile` on all three app sources — no syntax errors.
- Parsed every apps manifest with PyYAML — no structural/indentation errors.
- `kubectl apply --dry-run=client` couldn't run for real validation: this
  kubectl install insists on reaching a live API server even with
  `--validate=false`. Re-run this once a disposable cluster exists.
- Docker Desktop wasn't running locally, so the actual image builds are
  still unverified — do that before pushing to Docker Hub.

## Still open before integration

- Confirm the six final Docker Hub tags with A (assumed `1.0` here, matching
  the platform images).
- Build + push the three images once Docker Desktop / a registry login is
  available.
- Re-run manifest validation against a real (even single-node) cluster.
- Confirm ServiceLB is enabled on Master, per the note above.
