<!--
Eclipse Tractus-X - Industry Core Hub

Copyright (c) 2026 Contributors to the Eclipse Foundation

This work is made available under the terms of the
Creative Commons Attribution 4.0 International (CC-BY-4.0) license.

SPDX-License-Identifier: CC-BY-4.0
-->

# REED Dataspace (local, two-participant)

Your own self-contained REED Manufacturing Data Space — **not** Catena-X — for
learning and development. Two participants (REED-Supplier provider, REED-OEM
consumer), each with its own database, plus shared infra in Docker.

**Follow the step-by-step guide:** [`../../docs/reed/REED-DATASPACE-TUTORIAL.md`](../../docs/reed/REED-DATASPACE-TUTORIAL.md)

## TL;DR

```bash
cd deployment/reed-dataspace
./scripts/up-infra.sh                 # 1. Postgres + pgAdmin
./scripts/run-backend.sh supplier     # 2. terminal A -> :9000
./scripts/run-backend.sh oem          # 2. terminal B -> :9001
./scripts/seed.sh                     # 3. seed policies + classification + relation
./scripts/demo-exchange.sh            # 4. full MVP flow: classify->authorize->request->decide->contract->audit
./scripts/run-frontend.sh supplier    # 5. (optional) portal -> :5173
./scripts/run-frontend.sh oem         #    (optional) portal -> :5174
./scripts/down.sh                     # stop infra (add --purge to wipe data)
```

## Layout

| Path | Purpose |
| --- | --- |
| `docker-compose.yaml` | Postgres (2 DBs) + pgAdmin + optional Keycloak (`--profile secured`) |
| `init-db.sql` | Creates `reed_supplier` / `reed_oem` databases |
| `config/reed-supplier.yml` | Supplier backend config (BPN `BPNLREEDSUPP0001`, port 9000) |
| `config/reed-oem.yml` | OEM backend config (BPN `BPNLREEDOEM00001`, port 9001) |
| `scripts/*.sh` | Orchestration: infra, backends, frontends, seed, demo, teardown |
| `realm/reed-realm.json` | Minimal Keycloak realm for the optional secured path |

Ports: Postgres `5433`, pgAdmin `5051`, backends `9000/9001`, portals `5173/5174`,
Keycloak `8080` (secured only). Chosen to avoid clashing with
`deployment/local/docker-compose`.
