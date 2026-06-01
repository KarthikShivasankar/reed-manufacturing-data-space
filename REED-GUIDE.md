<!--
REED Manufacturing Data Space — Complete Guide

Copyright (c) 2026 Contributors to the Eclipse Foundation

This work is made available under the terms of CC-BY-4.0 (documentation) and
Apache-2.0 (code samples).

SPDX-License-Identifier: CC-BY-4.0
-->

# REED Manufacturing Data Space — The Complete Guide

> One document, in order: **what it is → how it works → how to run it → how to operate it**.
> Everything here has been validated against the code in this repository.

---

## Table of contents

1. [What REED is and why it exists](#1-what-reed-is-and-why-it-exists)
2. [Key concepts and terminology](#2-key-concepts-and-terminology)
3. [Architecture](#3-architecture)
4. [Repository layout](#4-repository-layout)
5. [The REED data model](#5-the-reed-data-model)
6. [The policy model (three layers)](#6-the-policy-model-three-layers)
7. [The authorization engine (decision order)](#7-the-authorization-engine-decision-order)
8. [The access-request workflow (state machine)](#8-the-access-request-workflow-state-machine)
9. [End-to-end workflow (the full picture)](#9-end-to-end-workflow-the-full-picture)
10. [Prerequisites](#10-prerequisites)
11. [Deployment A — your own REED dataspace (recommended)](#11-deployment-a--your-own-reed-dataspace-recommended)
12. [Deployment B — backend only](#12-deployment-b--backend-only)
13. [Deployment C — frontend only](#13-deployment-c--frontend-only)
14. [Deployment D — Kubernetes / Helm](#14-deployment-d--kubernetes--helm)
15. [Secured mode (Keycloak identity)](#15-secured-mode-keycloak-identity)
16. [Going sovereign (real EDC + DTR exchange)](#16-going-sovereign-real-edc--dtr-exchange)
17. [REED API reference](#17-reed-api-reference)
18. [Security and trust model](#18-security-and-trust-model)
19. [Testing](#19-testing)
20. [Operations and management](#20-operations-and-management)
21. [Troubleshooting](#21-troubleshooting)
22. [FAQ](#22-faq)
23. [License and attribution](#23-license-and-attribution)

---

## 1. What REED is and why it exists

**REED** is a **domain-specific manufacturing data space** layer built on top of the
[Eclipse Tractus-X **Industry Core Hub** (ICH)](https://github.com/eclipse-tractusx/industry-core-hub).

Manufacturing partners — OEMs, suppliers, service providers — need to share
sensitive data about **bulky parts** (process capability, fixtures, quality
evidence, simulation results, digital product passports) **selectively and
sovereignly**: a partner should be able to *discover that data exists* without
*receiving the confidential payload* until a contract is accepted, and every
access must be policy-governed and audited.

**The design decision:** do **not** rebuild a connector, registry, identity
system, or policy engine. Those are solved by the Tractus-X stack:

| Concern | Owner |
| --- | --- |
| Inter-company contract negotiation & data transfer | **EDC** (Eclipse Dataspace Connector) |
| Digital-twin discoverability (AAS shells + submodel descriptors) | **DTR** (Digital Twin Registry) |
| Confidential payload storage/retrieval | **Submodel service** |
| User login, roles, groups, tokens | **Keycloak** |
| BPN → endpoint resolution | **Discovery services** |

REED owns **only the manufacturing use-case layer**:

- a **data classification matrix** (what the data is and how sensitive it is),
- a **policy catalogue** (catalogue / contract / usage policies, rendered to EDC/ODRL),
- a **supply-chain relationship graph**,
- a **context-based authorization engine** (run before any EDC/DTR call),
- an **access-request workflow**, and
- an **audit trail**.

---

## 2. Key concepts and terminology

| Term | Meaning |
| --- | --- |
| **BPN / BPNL** | Business Partner Number (Legal) — a 16-char dataspace identity, e.g. `BPNLREEDSUPP0001`. Generic to dataspaces, not Catena-X specific. |
| **Asset class** | One of eight REED manufacturing data types (see §5). |
| **Classification** | The matrix entry for an asset class: sensitivity, discoverability, payload location, allowed purposes, obligations, prohibitions, default policy template. |
| **Sensitivity** | `public` → `consortium` → `restricted` → `confidential` → `regulated`. |
| **Discoverability** | Who may learn metadata exists: `public` / `consortium` / `project` / `bilateral` / `hidden`. |
| **Policy layer** | `catalogue` (discover?), `contract` (negotiate?), `usage` (obligations/prohibitions). |
| **Policy template** | A named, reusable policy of one layer; renders to an EDC/ODRL policy definition. |
| **ODRL** | Open Digital Rights Language — the JSON-LD policy format the EDC management API consumes. |
| **Authorization context** | Identity (BPN, roles, projects, membership/NDA/framework) + request (owner BPN, asset class, purpose, project). |
| **Access request** | A consumer's request to access an owner's asset; flows through a workflow. |
| **Principal** | The server-resolved identity of a caller (from a Keycloak token, or a trusted API-key "service" principal). |
| **Provider / Consumer** | The data **owner** vs. the **requester**. |

---

## 3. Architecture

### 3.1 How REED sits on the stack

```
        Users (OEM / Supplier / Service-provider)
                        │
                ┌───────▼────────┐
                │  REED Portal    │  ichub-frontend + reed-kit
                └───────┬────────┘
                        │  HTTPS (token / API key)
                ┌───────▼─────────────────────────────────────────┐
                │  REED Backend  (ichub-backend + services/reed)    │
                │                                                   │
                │  reed_security  → resolves trusted principal      │
                │  AuthorizationService → allow/deny + policy match │
                │  PolicyTemplateService → renders EDC/ODRL         │
                │  AccessRequestService → workflow                  │
                │  AuditService → evidence trail                    │
                │  Classification / SupplyChain services            │
                └───────┬───────────────────────────┬──────────────┘
                        │ (REED owns decisions)      │ (delegates to stack)
        ┌───────────────▼──────┐        ┌────────────▼───────────────┐
        │ PostgreSQL (REED      │        │ Optional sovereign layer:    │
        │ tables per participant)│       │ EDC ⇄ EDC, DTR, Submodel,    │
        └───────────────────────┘        │ Keycloak, Discovery, Vault   │
                                         └──────────────────────────────┘
```

### 3.2 The "two participants" model for a working dataspace

```
   REED-Supplier (provider)              REED-OEM (consumer)
   backend :9000  portal :5173           backend :9001  portal :5174
   db reed_supplier                      db reed_oem
   BPNLREEDSUPP0001                      BPNLREEDOEM00001
              \                                 /
               \___ shared infra (docker) _____/
                    Postgres :5433  pgAdmin :5051  Keycloak :8080 (optional)
```

Each participant runs its own backend, portal and database — exactly like two
real companies. Full design rationale:
[`docs/architecture/reed-manufacturing-data-space.md`](docs/architecture/reed-manufacturing-data-space.md).

---

## 4. Repository layout

```
ichub-backend/                            FastAPI backend (Python)
  models/metadata_database/reed/          REED SQLModel tables + enums (models.py, tables.py)
  models/services/reed/                   REED API (Pydantic) schemas
  managers/metadata_database/
    reed_repositories.py                  REED repositories (on shared BaseRepository)
    manager.py                            wires REED repos into RepositoryManager
  services/reed/                          REED business logic
    classification_service.py
    policy_template_service.py            + ODRL rendering
    supply_chain_service.py
    authorization_service.py              the context-based decision engine
    access_request_service.py             the workflow
    audit_service.py
    seed_service.py                       8 default templates + 8 classifications
  controllers/fastapi/routers/reed/
    reed_security.py                      principal resolution + role/admin guards
    v1/*.py                               classification, policy_template, supply_chain,
                                          authorization, access_request, audit, admin
  controllers/fastapi/app.py              registers REED routers + startup table creation
  tests/services/reed/                    REED unit tests (authz, ODRL, security)

ichub-frontend/src/features/reed-kit/     REED portal kit
  services/reedApi.ts                     typed API client
  data-classification/ policy-templates/  five feature folders (routes + page)
  access-requests/ authorization/ audit/

deployment/reed-dataspace/                YOUR OWN two-participant dataspace
  docker-compose.yaml  init-db.sql        shared infra
  config/reed-supplier.yml reed-oem.yml   participant backend configs
  realm/reed-realm.json                   optional Keycloak realm
  scripts/                                up-infra, run-backend, run-frontend, seed,
                                          demo-exchange, down

docs/
  reed/README.md                          REED module guide + API reference
  reed/REED-DATASPACE-TUTORIAL.md         step-by-step dataspace tutorial
  architecture/reed-manufacturing-data-space.md   reference architecture
  database/REED-DDL-public.sql            optional explicit DDL
```

---

## 5. The REED data model

REED persists five additive tables (created automatically on backend startup):
`reed_asset_classification`, `reed_policy_template`, `reed_supply_chain_relation`,
`reed_access_request`, `reed_audit_event`.

### 5.1 The eight asset classes

| Asset class | What it holds |
| --- | --- |
| `PartDigitalTwin` | Catalog/serialized/bulky part identity, BPN ownership, lifecycle state |
| `BillOfMaterial` | Parent/child part relationships, supplier links |
| `DigitalProductPassport` | Materials, recyclability, carbon footprint, compliance |
| `ProcessCapability` | Machine envelope, operations, tolerances, lead time |
| `FixtureHandlingStrategy` | Fixture design, lifting/handling constraints, setup |
| `ProductionStatus` | Capacity, order status, quality gates, delivery |
| `QualityEvidence` | Inspection reports, certificates, non-conformance |
| `SimulationResult` | Process simulation, energy use, risk/lead-time estimation |

### 5.2 The default classification matrix (seeded)

| Asset class | Sensitivity | Discoverability | Default policy template |
| --- | --- | --- | --- |
| PartDigitalTwin | consortium | consortium | `consortium-only` |
| BillOfMaterial | confidential | bilateral | `bilateral-supplier` |
| DigitalProductPassport | consortium | consortium | `dpp-read-only` |
| ProcessCapability | confidential | bilateral | `oem-only` |
| FixtureHandlingStrategy | confidential | bilateral | `bilateral-supplier` |
| ProductionStatus | restricted | project | `time-limited-pilot-access` |
| QualityEvidence | regulated | bilateral | `oem-only` |
| SimulationResult | confidential | bilateral | `simulation-service-only` |

> **Only metadata is published to DTR/EDC catalogues; the confidential payload stays
> in the submodel service until a contract is accepted.**

---

## 6. The policy model (three layers)

| Layer | Question it answers | Enforced by |
| --- | --- | --- |
| **catalogue** | Can a partner discover the metadata exists? | REED context + EDC catalogue visibility |
| **contract** | Can a partner negotiate access? | EDC/ODRL policy generated from a REED template |
| **usage** | What obligations/prohibitions attach to the data? | EDC usage policy + REED audit/workflow |

### 6.1 The eight default policy templates

| Template | Layer | Core constraints |
| --- | --- | --- |
| `public-metadata` | catalogue | none (metadata only) |
| `consortium-only` | catalogue | membership active |
| `bilateral-supplier` | contract | membership + framework agreement + NDA |
| `oem-only` | contract | membership + role `oem-manager` |
| `simulation-service-only` | contract | purpose = process-simulation; delete-after-90d; no AI training |
| `dpp-read-only` | usage | purpose = DPP read; no onward sharing |
| `time-limited-pilot-access` | contract | membership + contract expiry ≤ 30 days |
| `anonymized-benchmark-access` | usage | aggregate only; no re-identification; no raw download |

### 6.2 Rendering to EDC/ODRL

`GET /v1/reed/policy-templates/{name}/odrl` turns a template into the exact ODRL
body the Tractus-X EDC management API consumes. Example for `oem-only`:

```json
{
  "@type": "odrl:Set",
  "odrl:permission": [
    { "action": "odrl:use",
      "constraint": { "and": [
        { "leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active" },
        { "leftOperand": "reed:Role",            "operator": "odrl:eq", "rightOperand": "oem-manager" }
      ] } }
  ],
  "odrl:prohibition": [ { "action": "reed:onwardSharing" } ],
  "odrl:obligation":  [ { "action": "reed:audit" } ]
}
```

---

## 7. The authorization engine (decision order)

`POST /v1/reed/authorization/evaluate` runs **before** any EDC/DTR call. It is
deterministic and evaluates rules in this order:

1. **Owner shortcut** — caller BPN == owner BPN → **allow**.
2. **Admin shortcut** — caller has `reed-admin` role → **allow** (break-glass).
3. **Classification lookup** — no classification for the asset class → **deny** (default-deny).
4. **Discoverability gate**
   - `hidden` → deny (owner/admin only)
   - `public` → allow through this gate
   - `consortium` → requires active membership
   - `project` → requires membership in the matching project
   - `bilateral` → requires a supply-chain relationship with the owner
5. **Sensitivity escalation** — `confidential`/`regulated` additionally require an
   active **NDA** *and* an accepted **framework agreement**.
6. **Purpose binding** — the declared `usagePurpose` must be in the classification's
   `allowedPurposes`.

The response is `{ allowed, reasons[], matchedPolicyTemplate, requiredObligations[] }`.
Denied evaluations are written to the audit log.

---

## 8. The access-request workflow (state machine)

```
  submitted ──▶ under_review ──▶ approved ──▶ contracted ──▶ transferred
       │                          │
       └──────────────────────────┴──▶ rejected
                              (expired / revoked are terminal)
```

| Step | Endpoint | Who | Effect |
| --- | --- | --- | --- |
| Submit | `POST /access-requests` | consumer | creates request, picks default policy template, audits `access_requested` |
| Decide | `POST /access-requests/{id}/decision` | **owner** only | approve/reject, audits `access_approved`/`access_rejected` |
| Contract | `POST /access-requests/{id}/contract` | party | records EDC agreement (+transfer), audits `contract_negotiated`/`data_transferred` |

Every transition writes a `reed_audit_event`.

---

## 9. End-to-end workflow (the full picture)

```
 1. Provider classifies a bulky-part asset (REED classification matrix)
 2. Provider stores the payload in the submodel service (metadata only to catalogue)
 3. (sovereign) AAS shell + submodel descriptors created in DTR
 4. (sovereign) EDC asset + access/contract policy + contract definition created
                using the ODRL rendered from the REED policy template
 5. Consumer discovers the supplier/part (BPN + discovery)
 6. Consumer retrieves the catalogue → sees only permitted metadata
 7. Consumer calls REED authorize → allow/deny + matched policy + obligations
 8. Consumer submits an access request
 9. Provider decides (approve)
10. EDC negotiates the contract under the REED policy template
11. Data is transferred through the EDC data plane
12. REED records the agreement/transfer + audit event
13. REED updates the supply-chain / DPP / audit views
```

In this repository, steps 1–2, 5–9, 12–13 are fully implemented; steps 3–4 and
10–11 are the optional **sovereign** layer (§16) — today the `contract` step
records a *simulated* EDC agreement so you can learn the full flow without EDC.

---

## 10. Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Docker + Compose v2 | recent | shared infra (Postgres, pgAdmin, optional Keycloak) |
| Python | 3.12 | backend |
| Node.js + npm | 18+ | frontend |
| curl, jq | any | driving / reading the API |

Free these ports: `5433` (Postgres), `5051` (pgAdmin), `9000`/`9001` (backends),
`5173`/`5174` (portals), `8080` (Keycloak, secured mode only).

No Catena-X membership, BPN registration, or external IdP is required.

---

## 11. Deployment A — your own REED dataspace (recommended)

This brings up a complete, self-contained two-participant dataspace.

### Step 1 — start shared infrastructure
```bash
cd deployment/reed-dataspace
./scripts/up-infra.sh
```
Starts Postgres (creating `reed_supplier` + `reed_oem`) and pgAdmin
(http://localhost:5051, `admin@reed.local` / `admin`). Wait for `Infrastructure ready`.

### Step 2 — start both participant backends (two terminals)
```bash
# Terminal A
cd deployment/reed-dataspace && ./scripts/run-backend.sh supplier   # → http://localhost:9000/docs

# Terminal B
cd deployment/reed-dataspace && ./scripts/run-backend.sh oem        # → http://localhost:9001/docs
```
First run creates a virtualenv at `.reed-venv` and installs `requirements.txt`.
Each backend logs `[REED] Metadata tables ensured: ...` (tables auto-created).
Connector/DTR "START UP ERROR" warnings are **expected and harmless** here.

### Step 3 — seed policies, classifications and the supply-chain relation
```bash
cd deployment/reed-dataspace
./scripts/seed.sh
```
Expected:
```
{"templates_created":8,"classifications_created":8}   # supplier
{"templates_created":8,"classifications_created":8}   # OEM
{... "relationType":"supplies_to" ...}
```

### Step 4 — run the full exchange
```bash
./scripts/demo-exchange.sh
```
Prints each step: **classify → render ODRL → authorize → request → decide →
contract → audit (3 events)**. Try a denial:
```bash
curl -s -X POST http://localhost:9000/v1/reed/authorization/evaluate \
  -H "content-type: application/json" \
  -d '{"bpn":"BPNLREEDOEM00001","ownerBpn":"BPNLREEDSUPP0001","assetClass":"ProcessCapability",
       "usagePurpose":"reed.supply-chain.planning:1","membershipActive":true,
       "frameworkAgreement":"DataExchangeGovernance:1.0","ndaActive":false}' | jq
# → allowed:false, "confidential data requires an active NDA."
```

### Step 5 — (optional) open the portals (two more terminals)
```bash
./scripts/run-frontend.sh supplier    # http://localhost:5173
./scripts/run-frontend.sh oem         # http://localhost:5174
```
In the portal → **Add Features** → enable **REED Manufacturing Data Space**.
Five screens: Data Classification, Policy Templates, Access Requests,
Authorization Simulator, Audit Trail.

### Step 6 — tear down
```bash
./scripts/down.sh           # stop infra, keep data
./scripts/down.sh --purge   # stop infra and wipe the database volume
# Stop backends/portals with Ctrl-C in their terminals.
```

Detailed narrative + learning notes:
[`docs/reed/REED-DATASPACE-TUTORIAL.md`](docs/reed/REED-DATASPACE-TUTORIAL.md).

---

## 12. Deployment B — backend only

```bash
cd ichub-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point database.connection_string at your PostgreSQL in the config file.
python main.py --config ./config/configuration.yaml --host 0.0.0.0 --port 8000
```
Then:
```bash
curl -X POST http://localhost:8000/v1/reed/admin/seed
# Swagger UI: http://localhost:8000/docs → "REED Manufacturing Data Space" group
```

---

## 13. Deployment C — frontend only

```bash
cd ichub-frontend
npm install
VITE_ICHUB_BACKEND_URL=http://localhost:8000/v1 npm run dev   # http://localhost:5173
```
Build for production:
```bash
npm run build      # outputs dist/
```

---

## 14. Deployment D — Kubernetes / Helm

The REED layer ships **inside the backend image** and creates its tables on
startup, so no chart changes are required.

1. Deploy Industry Core Hub via Helm (see [`INSTALL.md`](INSTALL.md) and
   [`docs/umbrella/umbrella-deployment-guide.md`](docs/umbrella/umbrella-deployment-guide.md)).
2. After the backend is up, seed once: `POST /v1/reed/admin/seed` (requires
   `reed-admin` / API key when auth is enabled).
3. If your operator provisions schema out-of-band, apply
   [`docs/database/REED-DDL-public.sql`](docs/database/REED-DDL-public.sql); the
   startup table-creation hook then becomes a no-op.

---

## 15. Secured mode (Keycloak identity)

The tutorial path runs with `authorization.enabled: false` (trusted service
principal). To use real per-user identity where BPN/roles come from a validated
token and cannot be spoofed:

1. `./scripts/up-infra.sh --secured` (imports realm `REED` from
   `deployment/reed-dataspace/realm/reed-realm.json`, with roles `reed-admin` /
   `oem-manager` / `supplier-owner`, two demo users, and a `bpn` claim mapper).
2. In `config/reed-supplier.yml` and `reed-oem.yml` set
   `authorization.enabled: true` and `authorization.keycloak.enabled: true`.
3. Restart the backends. Now `/reed/*` requires a bearer token (or API key);
   `reed_security` derives identity from the token; admin/write endpoints require
   `reed-admin`; access-request decisions are restricted to the owner; audit is
   scoped to the caller's BPN.

---

## 16. Going sovereign (real EDC + DTR exchange)

Today the `contract` step records a *simulated* EDC agreement. To make the
cross-company transfer real:

1. Deploy **Tractus-X EDC** control/data planes, **DTR**, a **submodel service**,
   and **Vault** for each participant — via the Tractus-X **Umbrella** chart or the
   [MXD tutorial](https://github.com/eclipse-tractusx/tutorial-resources/tree/main/mxd).
2. Point each participant's `consumer`/`provider` config blocks at its EDC/DTR.
3. Extend the access-request `contract` step to call the EDC management API,
   using the ODRL produced by `GET /reed/policy-templates/{name}/odrl` as the
   policy-definition body, then store the **real** agreement/transfer IDs.

At that point REED publishes only discoverable metadata to DTR/EDC, negotiates the
contract through EDC under the REED policy template, transfers the payload through
the EDC data plane, and audits the real agreement — the complete sovereign flow.

---

## 17. REED API reference

Base path `/<API_V1>` (default `/v1`). Full table + curl walkthrough in
[`docs/reed/README.md`](docs/reed/README.md).

| Area | Method & path |
| --- | --- |
| Classification | `GET /reed/classification`, `GET /reed/classification/{assetClass}`, `POST` *(admin)*, `PATCH /{assetClass}` *(admin)* |
| Policy templates | `GET /reed/policy-templates`, `GET /{name}`, `GET /{name}/odrl`, `POST` *(admin)*, `DELETE /{name}` *(admin)* |
| Supply chain | `GET /reed/supply-chain/relations`, `GET /relations/{bpn}`, `POST /relations` |
| Authorization | `POST /reed/authorization/evaluate` |
| Access requests | `POST /reed/access-requests`, `GET`, `GET /{id}`, `POST /{id}/decision`, `POST /{id}/contract` |
| Audit | `GET /reed/audit/events` |
| Admin | `POST /reed/admin/seed` *(admin)* |

Common calls:
```bash
API=http://localhost:9000/v1
curl -X POST $API/reed/admin/seed
curl $API/reed/classification | jq
curl $API/reed/policy-templates/simulation-service-only/odrl | jq
curl -X POST $API/reed/authorization/evaluate -H 'content-type: application/json' -d '{
  "bpn":"BPNLREEDOEM00001","ownerBpn":"BPNLREEDSUPP0001","assetClass":"ProcessCapability",
  "usagePurpose":"reed.supply-chain.planning:1","membershipActive":true,
  "frameworkAgreement":"DataExchangeGovernance:1.0","ndaActive":true,"project":"reed-pilot","projects":["reed-pilot"]}' | jq
```

---

## 18. Security and trust model

- **Keycloak users**: identity (BPN, roles, projects, membership / framework / NDA)
  is derived **server-side from the validated token** by `reed_security`. Body
  values are ignored for token callers → no spoofing.
- **API key**: treated as a trusted **service principal** (granted `reed-admin`),
  consistent with how the rest of ICH treats the shared key.
- **Guards**: admin/write endpoints require `reed-admin`; access-request decisions
  are owner-only; audit and listings are scoped to the caller's BPN.
- The learning dataspace runs auth-disabled (every caller is the trusted service
  principal) so you can explore without tokens.

Details: [`docs/reed/README.md`](docs/reed/README.md) §1.4.

---

## 19. Testing

```bash
# Backend REED unit tests (authorization branches, ODRL rendering, security guards)
cd ichub-backend
python -m pytest tests/services/reed -q

# Full backend suite
python -m pytest tests -q

# Frontend production build (includes the REED kit)
cd ../ichub-frontend
npm run build
```

---

## 20. Operations and management

| Action | Command |
| --- | --- |
| Inspect a participant DB | `docker exec -it reed_postgres psql -U reed -d reed_supplier` |
| List REED tables | inside psql: `\dt public.reed_*` |
| Browse data visually | pgAdmin → http://localhost:5051 |
| Tail backend logs | watch its terminal (or run with `> file.log 2>&1 &`) |
| Re-seed (refresh built-ins) | `curl -X POST http://localhost:9000/v1/reed/admin/seed?overwrite=true` |
| Reset a participant | drop+recreate its database, then restart its backend |
| Stop infra (keep data) | `./scripts/down.sh` |
| Stop infra (wipe data) | `./scripts/down.sh --purge` |

---

## 21. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Backend loops on `Database not ready ... port 5433` | Infra not up → run `./scripts/up-infra.sh` first |
| `Connection refused ... :8080` at startup | Keycloak not running + auth disabled → harmless |
| `[]` from every REED endpoint | You haven't run `./scripts/seed.sh` |
| `403` on seed/create/delete | Auth enabled but no `reed-admin` token/API key |
| `port is already allocated` | Another stack uses 5433/9000/5173 → stop it or change ports |
| Portal can't reach backend | Check `VITE_ICHUB_BACKEND_URL` and CORS `allow_origins` in the config |
| `DetachedInstanceError` | Already fixed; ensure you're on the latest code |

---

## 22. FAQ

**Is this Catena-X?** No. REED stands up *your own* dataspace. It reuses Tractus-X
open-source components but requires no Catena-X membership or onboarding.

**Do I need EDC/DTR to try REED?** No. The classification, policy, authorization,
access-request and audit features work standalone. EDC/DTR is the optional
sovereign layer (§16).

**Where does the confidential payload live?** In the submodel service — never in
DTR/EDC catalogues, which only carry discoverable metadata.

**Can a user fake their BPN or role?** No. With Keycloak, identity comes from the
validated token, not the request body (§18).

**How do I add a new asset class or policy?** `POST /reed/classification` and
`POST /reed/policy-templates` (admin), or edit `services/reed/seed_service.py`.

---

## 23. License and attribution

Code: **Apache-2.0**. Documentation: **CC-BY-4.0**. This project builds on
[Eclipse Tractus-X Industry Core Hub](https://github.com/eclipse-tractusx/industry-core-hub)
and retains its `LICENSE`, `LICENSE_non-code`, `NOTICE.md`, and `AUTHORS.md`. The
original ICH README is preserved at
[`docs/industry-core-hub-readme.md`](docs/industry-core-hub-readme.md).
