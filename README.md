<!--
REED Manufacturing Data Space

Copyright (c) 2026 Contributors to the Eclipse Foundation

This work is made available under the terms of the
Apache License 2.0 (code) and CC-BY-4.0 (documentation).

SPDX-License-Identifier: Apache-2.0
-->

# REED Manufacturing Data Space

A **domain-specific manufacturing data space** layer built on top of the
[Eclipse Tractus-X **Industry Core Hub**](https://github.com/eclipse-tractusx/industry-core-hub).
REED lets manufacturing partners (OEMs, suppliers, service providers) **classify**
bulky-part data, attach **sovereign data-sharing policies**, decide access with a
**context-based authorization engine**, run an **access-request workflow**, and keep
a full **audit trail** — all without rebuilding a connector, registry, identity
system, or policy engine. Those responsibilities stay with the proven Tractus-X
stack (EDC, DTR, Keycloak); REED owns only the manufacturing use-case layer.

> 📖 **New here? Read [`REED-GUIDE.md`](REED-GUIDE.md)** — one complete, ordered
> guide covering concepts → architecture → step-by-step deployment → workflow →
> operations.

> This repository is a fork of Industry Core Hub with the REED layer added. The
> original project README is preserved at
> [`docs/industry-core-hub-readme.md`](docs/industry-core-hub-readme.md).

---

## Table of contents

- [What REED adds](#what-reed-adds)
- [Concepts in 60 seconds](#concepts-in-60-seconds)
- [Repository layout](#repository-layout)
- [Quickstart — run your own REED dataspace](#quickstart--run-your-own-reed-dataspace)
- [Run the backend on its own](#run-the-backend-on-its-own)
- [Run the frontend on its own](#run-the-frontend-on-its-own)
- [REED API reference](#reed-api-reference)
- [Security & trust model](#security--trust-model)
- [Testing](#testing)
- [Going sovereign (real EDC + DTR)](#going-sovereign-real-edc--dtr)
- [Documentation index](#documentation-index)
- [License](#license)

---

## What REED adds

| Capability | Endpoints (`/v1/reed/...`) | Backend code |
| --- | --- | --- |
| **Data classification matrix** (DMP-derived) | `/classification` | `services/reed/classification_service.py` |
| **Policy catalogue** + EDC/ODRL rendering | `/policy-templates`, `/policy-templates/{name}/odrl` | `services/reed/policy_template_service.py` |
| **Supply-chain graph** | `/supply-chain/relations` | `services/reed/supply_chain_service.py` |
| **Context-based authorization** | `/authorization/evaluate` | `services/reed/authorization_service.py` |
| **Access-request workflow** | `/access-requests` (+ `/decision`, `/contract`) | `services/reed/access_request_service.py` |
| **Audit trail** | `/audit/events` | `services/reed/audit_service.py` |
| **Seed defaults** (8 templates + 8 classes) | `/admin/seed` | `services/reed/seed_service.py` |

Plus a **portal kit** (`ichub-frontend/src/features/reed-kit/`) with five screens:
Data Classification, Policy Templates, Access Requests, Authorization Simulator,
and Audit Trail.

## Concepts in 60 seconds

- **8 asset classes** — `PartDigitalTwin`, `BillOfMaterial`, `DigitalProductPassport`,
  `ProcessCapability`, `FixtureHandlingStrategy`, `ProductionStatus`,
  `QualityEvidence`, `SimulationResult`.
- **Classification matrix** — each class maps to a *sensitivity*, *discoverability*,
  *payload location*, *allowed purposes*, *obligations/prohibitions*, and a *default
  policy template*. Only metadata is published to DTR/EDC; payloads stay in the
  submodel service until a contract is accepted.
- **Three policy layers** — *catalogue* (can you discover it?), *contract* (can you
  negotiate?), *usage* (obligations/prohibitions). Templates render to **EDC/ODRL**.
- **Context-based authorization** — combines Keycloak token claims (BPN, roles,
  projects, membership/NDA/framework) + the classification + the supply-chain graph
  to return *allow/deny + matched policy + required obligations*. Default-deny.
- **Audit** — every decision and workflow step is recorded: participant, user, BPN,
  asset, purpose, policy, agreement, timestamp, outcome.

Full design: [`docs/architecture/reed-manufacturing-data-space.md`](docs/architecture/reed-manufacturing-data-space.md).

## Repository layout

```
ichub-backend/                     FastAPI backend (Python)
  models/metadata_database/reed/   REED SQLModel tables + enums
  models/services/reed/            REED API (Pydantic) schemas
  managers/metadata_database/      reed_repositories.py + manager wiring
  services/reed/                   REED business logic (incl. authorization engine)
  controllers/fastapi/routers/reed/ REED routers + reed_security.py (principal/guards)
  tests/services/reed/             REED unit tests
ichub-frontend/                    React + MUI portal (Vite)
  src/features/reed-kit/           REED portal kit (API client + 5 pages)
deployment/reed-dataspace/         Your own 2-participant REED dataspace (MXD-style)
docs/reed/                         REED module guide + dataspace tutorial
docs/architecture/                 REED reference architecture
docs/database/REED-DDL-public.sql  Optional explicit DDL for the REED tables
```

## Quickstart — run your own REED dataspace

The fastest path: a self-contained **two-participant** data space (REED-Supplier
provider + REED-OEM consumer), **not** Catena-X, all on your machine.

**Prerequisites:** Docker + Compose v2, Python 3.12, Node 18+, `curl`, (optional) `jq`.

```bash
cd deployment/reed-dataspace
./scripts/up-infra.sh                 # 1. Postgres (a DB per participant) + pgAdmin
./scripts/run-backend.sh supplier     # 2. terminal A → http://localhost:9000/docs
./scripts/run-backend.sh oem          # 2. terminal B → http://localhost:9001/docs
./scripts/seed.sh                     # 3. seed policies + classifications + supply-chain relation
./scripts/demo-exchange.sh            # 4. full MVP flow, printed step by step
./scripts/run-frontend.sh supplier    # 5. (optional) portal → http://localhost:5173
./scripts/run-frontend.sh oem         #    (optional) portal → http://localhost:5174
./scripts/down.sh                     # stop infra (add --purge to wipe data)
```

`demo-exchange.sh` walks the full REED flow: **classify → render ODRL → authorize →
request → decide → contract → audit**. Full walkthrough, the secured/Keycloak path,
and the sovereign EDC+DTR upgrade are in
[`docs/reed/REED-DATASPACE-TUTORIAL.md`](docs/reed/REED-DATASPACE-TUTORIAL.md).

| Participant | Role | BPN | Backend | Portal | DB |
| --- | --- | --- | --- | --- | --- |
| REED-Supplier | provider | `BPNLREEDSUPP0001` | :9000 | :5173 | `reed_supplier` |
| REED-OEM | consumer | `BPNLREEDOEM00001` | :9001 | :5174 | `reed_oem` |

## Run the backend on its own

```bash
cd ichub-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Edit config so database.connection_string points at your PostgreSQL.
python main.py --config ./config/configuration.yaml --host 0.0.0.0 --port 8000
```

On startup the backend logs `[REED] Metadata tables ensured: ...` (the five REED
tables are created automatically). Then seed defaults and open Swagger:

```bash
curl -X POST http://localhost:8000/v1/reed/admin/seed
# Swagger UI: http://localhost:8000/docs  →  "REED Manufacturing Data Space" group
```

## Run the frontend on its own

```bash
cd ichub-frontend
npm install
VITE_ICHUB_BACKEND_URL=http://localhost:8000/v1 npm run dev   # http://localhost:5173
```

Open the portal → **Add Features** → enable **REED Manufacturing Data Space**.

## REED API reference

See [`docs/reed/README.md`](docs/reed/README.md) for the complete endpoint table and
a `curl` walkthrough. Highlights:

```bash
API=http://localhost:8000/v1
curl -X POST $API/reed/admin/seed                      # seed catalogue + matrix
curl $API/reed/classification                          # the DMP-derived matrix
curl $API/reed/policy-templates/oem-only/odrl          # render a policy to EDC/ODRL
curl -X POST $API/reed/authorization/evaluate -H 'content-type: application/json' -d '{...}'
curl -X POST $API/reed/access-requests        -H 'content-type: application/json' -d '{...}'
```

## Security & trust model

- **Keycloak users**: identity (BPN, roles, projects, membership/NDA/framework) is
  derived **server-side from the validated token** and cannot be spoofed via the
  request body.
- **API key**: treated as a trusted *service principal* (granted `reed-admin`), as
  the rest of Industry Core Hub treats the shared key.
- **Guards**: admin/write endpoints require `reed-admin`; access-request decisions
  are restricted to the data owner; audit/listings are scoped to the caller's BPN.

Details: [`docs/reed/README.md`](docs/reed/README.md) §1.4. The learning dataspace
runs with auth disabled (every caller is the trusted service principal) so you can
explore without tokens; switch on Keycloak via the tutorial's "secured" path.

## Testing

```bash
cd ichub-backend && python -m pytest tests/services/reed -q     # REED unit tests
cd ichub-frontend && npm run build                              # frontend build
```

## Going sovereign (real EDC + DTR)

REED owns the *decision and policy* layer; the dataspace demo records a *simulated*
EDC agreement. To make the cross-company transfer real, add Tractus-X EDC control/
data planes, DTR, a submodel service and Vault per participant via the
[Umbrella chart](docs/umbrella/umbrella-deployment-guide.md) or the
[MXD tutorial](https://github.com/eclipse-tractusx/tutorial-resources/tree/main/mxd),
then wire the access-request `contract` step to the EDC management API using the
ODRL body that `/reed/policy-templates/{name}/odrl` already produces. See
[`docs/reed/REED-DATASPACE-TUTORIAL.md`](docs/reed/REED-DATASPACE-TUTORIAL.md) §10.

## Documentation index

| Doc | What it covers |
| --- | --- |
| [`docs/reed/README.md`](docs/reed/README.md) | REED backend module guide + API reference + curl walkthrough |
| [`docs/reed/REED-DATASPACE-TUTORIAL.md`](docs/reed/REED-DATASPACE-TUTORIAL.md) | Step-by-step MXD-style two-participant dataspace tutorial |
| [`docs/architecture/reed-manufacturing-data-space.md`](docs/architecture/reed-manufacturing-data-space.md) | REED reference architecture & design decisions |
| [`deployment/reed-dataspace/README.md`](deployment/reed-dataspace/README.md) | Dataspace deployment quick reference |
| [`docs/database/REED-DDL-public.sql`](docs/database/REED-DDL-public.sql) | Optional explicit DDL for the REED tables |
| [`docs/industry-core-hub-readme.md`](docs/industry-core-hub-readme.md) | Original Industry Core Hub README |

## License

Code is licensed under the **Apache License 2.0**; documentation under
**CC-BY-4.0**. This project builds on
[Eclipse Tractus-X Industry Core Hub](https://github.com/eclipse-tractusx/industry-core-hub)
and retains its `NOTICE.md`, `LICENSE`, and `AUTHORS.md`.
