# Orchestrator: two-developer handoff

This plan is for the 01‑edu Orchestrator project. We will reuse our [Play With Containers](https://platform.zone01.gr/git/cgkaldan/play-with-containers) Python services and Dockerfiles, deploy six images to a two-node K3s cluster in Vagrant, and meet the mandatory audit before considering bonuses. The project repository is [orchestrator](https://platform.zone01.gr/git/cgkaldan/orchestrator).

## How we work

Both developers are learning Kubernetes. Work in small, reviewable commits and explain each command and manifest before relying on it. An LLM helper should ask one useful prediction/diagnostic question at a time, then let the developer test and explain the result. It may write code after the concept is understood. Avoid optional features and long lectures. Neither developer should silently implement or rewrite the other's ownership area.

Developer A is the project owner working on the cluster and stateful platform. Developer B owns image delivery and application workloads. This is an approximately equal split: both write Kubernetes manifests, test them, review each other's work, and must be able to explain the entire system in the audit.

## Day-zero contract (agree before parallel coding)

Spend one short kickoff agreeing and committing these names. Afterwards, each track can work on its own branch without waiting for the other's code.

| Contract | Agreed value / rule |
| --- | --- |
| Branches | `feature/cluster-stateful` (A), `feature/apps-hpa` (B); merge by reviewed PRs |
| Namespace | `default`, because the audit uses `kubectl get all` without `-n` |
| Service DNS names | `inventory-database`, `billing-database`, `rabbit-queue`, `inventory-app`, `billing-app`, `api-gateway-app` |
| Internal ports | PostgreSQL `5432`, RabbitMQ `5672`, Inventory `8080`, Gateway `3000` |
| Database names | `movies_db` for Inventory; `orders` for Billing to match the audit's `psql` instructions (the Python app accepts this through `BILLING_DB_NAME`) |
| Queue | `billing_queue` |
| Images | Six public, version-tagged images in one agreed Docker Hub namespace; no `latest` tag in manifests |
| Credentials | Ignored local `.env`; Kubernetes Secret(s) contain database and RabbitMQ usernames/passwords; tracked manifests contain references, never real values |
| Gateway access | A stable host-reachable `:3000` endpoint; B validates this on the Vagrant network |
| Storage | Database PVCs must remain usable if their pods move between Master and Agent nodes |

The actual Docker Hub namespace and Vagrant private IPs are decided together before implementation. Do not share Docker Hub passwords: use collaborator access if available, or let one release owner publish the final six images. Each developer can build and test their own three images first.

Use the existing `srcs/<service>/Dockerfile` layout from Play With Containers, plus `Manifests/platform/` (A), `Manifests/apps/` (B), `Scripts/` (A), `Vagrantfile` (A), and `orchestrator.sh` (A). This differs slightly from the sample tree only by keeping each Dockerfile next to its source. Copy the six service sources into this repo once as a baseline so a fresh clone can build every image without depending on a sibling checkout. A and B write separate working notes; the final README is assembled during integration to avoid edit conflicts.

## Developer A — cluster and stateful platform

Owns `Vagrantfile`, `orchestrator.sh`, `Scripts/`, `Manifests/platform/`, and the Inventory DB, Billing DB, and RabbitMQ image definitions. Do not edit B's app manifests.

1. Create exactly two Vagrant VMs, `Master` and `Agent`, with unique hostnames and a network on which they can reach each other. Install K3s server and join the agent. Configure host `kubectl` without committing kubeconfig or the K3s join token.
2. Make `./orchestrator.sh create`, `start`, and `stop` reproducible. `stop` should halt, not destroy, the VMs and database data. Document what each command changes.
3. Provide a reproducible way to create Kubernetes Secrets from ignored local credentials. Ensure every database and RabbitMQ credential used by the pods is sourced from a Secret, not a normal manifest literal.
4. Deploy both PostgreSQL databases as one-replica StatefulSets with Services and PVCs. Deploy RabbitMQ with a Service. Keep the service names and ports from the contract.
5. Provide storage shared between the two VM nodes and demonstrate that a database pod can be rescheduled onto the other node while its data remains. A simple NFS share from the Master VM is an acceptable school-project approach; document that the Master remains a storage single point of failure. Do not rely on K3s's default `local-path` class for the cross-node claim.
6. Verify `kubectl get nodes` shows two `Ready` nodes, database PVCs are `Bound`, the DBs accept connections, and `kubectl top pods` works so B's CPU HPAs have metrics.

Independent tests before B merges: Vagrant boot/reboot, two Ready nodes, Secret key names (not values), DB tables and a test row surviving database pod recreation and cross-node rescheduling, RabbitMQ service reachable. Use placeholder workloads if needed; A does not require app manifests to prove these.

## Developer B — images and application delivery

Owns the Inventory, Billing, and Gateway image definitions and source packaging, `Manifests/apps/`, and app/testing notes. Do not edit A's Vagrant, storage, or platform manifests.

1. Build and test the three Python application images from this repo. Coordinate the six final Docker Hub tags with A, publish the app images, and verify the manifests refer to the student's public Docker Hub images rather than local-only tags.
2. Deploy `inventory-app` and `api-gateway-app` as Deployments with Services. Expose only the Gateway externally on port `3000`; the other services use internal Kubernetes DNS. Check whether the supplied architecture actually requires an Ingress before adding one, and be ready to explain how Ingress differs from the API Gateway.
3. Add a CPU HorizontalPodAutoscaler for each Deployment: min `1`, max `3`, target `60%`. Set CPU requests in the pods and verify metrics are available; an HPA object with an `<unknown>` CPU target is not a finished test.
4. Deploy `billing-app` as a one-replica StatefulSet, consuming `billing_queue`. For the audit's stop/start test, scale this StatefulSet to `0` and then back to `1`; deleting its pod alone would cause Kubernetes to replace it immediately.
5. Refer to A's Secret names/keys and Service DNS names exactly as written in the contract. Add readiness checks where they help keep the Gateway from routing to an unready application.
6. Test the app images locally and validate manifests independently (`kubectl apply --dry-run=client` plus a disposable one-node K3s cluster if available). Full service-to-database tests wait only for final integration, not for B's implementation work.

Independent tests before A merges: image builds and pulls by exact tag, Python unit tests, manifest validation, Deployment/StatefulSet/HPA object shapes, and Gateway Service routing in a temporary cluster if available. B does not need A's finished two-node Vagrant setup to write or validate these.

## Integration and audit rehearsal

Merge the two branches only after each track has its own evidence. Then run the complete flow from a fresh clone: create the two VMs, verify host `kubectl`, apply Secrets and manifests, pull all six Docker Hub images, inspect resources/volumes/HPAs, and make Postman movie POST/GET and Billing POST requests through the Gateway. Scale Billing to `0`, confirm a new request still returns `200` while the order is absent from PostgreSQL, scale back to `1`, and confirm the queued order appears. Restore all workloads to their normal replica counts afterwards.

The audit's Python project text contains some inconsistent names (for example, it calls the Billing database `orders` and elsewhere describes a queue-only consumer as reachable on `8080`). Prefer explicit, testable contracts above and explain any discrepancy rather than silently changing application behavior. Both developers cross-review one manifest from the other track and rehearse the theory: nodes/control plane, Pod/Service/Ingress/Deployment/StatefulSet, PVC/PV, Secret, metrics/HPA, and how `kubectl` reaches the API server.

## Learning checkpoint before implementation

Before writing the first Kubernetes manifest, each developer should be able to answer in their own words: What does a Pod run, what does a Service provide when a Pod is replaced, and which part of K3s decides where a Pod runs? Use prediction → small experiment → explanation, not copied definitions.

Useful primary references: [K3s quick start](https://docs.k3s.io/quick-start), [K3s storage](https://docs.k3s.io/add-ons/storage), [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/), [Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/), and [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/).

### Prompt for Developer B's LLM helper

> I am Developer B for this Orchestrator project. Read this entire plan and the project subject/audit. Help me own only image delivery and the application manifests. I am learning Kubernetes: ask one important question at a time, let me predict and run a small test, correct my reasoning with evidence, then write code when I understand the step. Do not implement Developer A's files. Keep commits small, explain unfamiliar commands briefly, never commit real credentials, and stop at an integration boundary instead of guessing A's names or IPs.
