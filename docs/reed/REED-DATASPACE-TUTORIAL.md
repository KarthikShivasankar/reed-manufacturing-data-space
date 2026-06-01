<!--
Eclipse Tractus-X - Industry Core Hub

Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This work is made available under the terms of the
Creative Commons Attribution 4.0 International (CC-BY-4.0) license,
which is available at
https://creativecommons.org/licenses/by/4.0/legalcode.

SPDX-License-Identifier: CC-BY-4.0
-->

# REED Dataspace — Hands-on Tutorial

This is the REED equivalent of the Tractus-X **Minimum Dataspace (MXD)** tutorial.
It stands up **your own** two-participant manufacturing data space — **not** the
public Catena-X network — entirely on your machine, and walks you through the
full REED data-exchange flow step by step.

You will run:

| Participant | Role | BPN | Backend | Portal |
| --- | --- | --- | --- | --- |
| **REED-Supplier** | data **provider** (owns bulky-part data) | `BPNLREEDSUPP0001` | http://localhost:9000 | http://localhost:5173 |
| **REED-OEM** | data **consumer** | `BPNLREEDOEM00001` | http://localhost:9001 | http://localhost:5174 |

Shared infrastructure (one Postgres with a database per participant, pgAdmin,
and an optional Keycloak) runs in Docker. All files live in
[`deployment/reed-dataspace/`](../../deployment/reed-dataspace).

> **Mental model (how this differs from MXD).** MXD gives you two *EDC connectors*
> (Alice/Bob) and lets you exchange opaque assets. REED sits one layer higher: it
> owns the *manufacturing use-case* — what the data **is** (classification), **who**
> may see it (context-based authorization), **under which policy** (the catalogue),
> and **what happened** (audit). The EDC/DTR connectors are an optional lower layer
> you bolt on later (see §8 "Going sovereign").

---

## 1. Prerequisites

- **Docker** + **Docker Compose v2** (`docker compose version`).
- **Python 3.12** (for the backends).
- **Node.js 18+** and **npm** (for the portals).
- A POSIX shell (`bash`), `curl`, and optionally `jq` for pretty output.
- Free ports: `5433` (Postgres), `5051` (pgAdmin), `9000/9001` (backends),
  `5173/5174` (portals), and `8080` (only if you use the secured profile).

No Catena-X membership, BPN registration, or external IdP is required.

---

## 2. Architecture of your REED dataspace

```
        ┌─────────────────────────┐          ┌─────────────────────────┐
        │   REED-Supplier (prov.) │          │     REED-OEM (cons.)    │
        │  backend  :9000         │          │  backend  :9001         │
        │  portal   :5173         │          │  portal   :5174         │
        │  db: reed_supplier      │          │  db: reed_oem           │
        └───────────┬─────────────┘          └───────────┬─────────────┘
                    │                                     │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Shared infra (docker compose)│
                    │  Postgres :5433  pgAdmin :5051 │
                    │  Keycloak :8080  (optional)    │
                    └────────────────────────────────┘
```

Each participant has its **own database**, so their REED state (classifications,
policies, supply-chain graph, access requests, audit) is isolated — just like two
real companies running separate instances.

---

## 3. Step 1 — Start the shared infrastructure

```bash
cd deployment/reed-dataspace
./scripts/up-infra.sh
```

This starts Postgres (creating the `reed_supplier` and `reed_oem` databases) and
pgAdmin. When it prints `Infrastructure ready`, verify:

```bash
docker exec reed_postgres psql -U reed -d reed -c "\l" | grep reed_
# reed_oem and reed_supplier should be listed
```

Browse the databases anytime at **http://localhost:5051** (`admin@reed.local` / `admin`),
connecting to host `postgres`, user `reed`, password `reed`.

---

## 4. Step 2 — Start the two participant backends

Open **two terminals** (each runs in the foreground so you can watch the logs).
The first run creates a Python virtualenv at `.reed-venv` and installs deps.

```bash
# Terminal A — Supplier (provider)
cd deployment/reed-dataspace
./scripts/run-backend.sh supplier        # -> http://localhost:9000/docs

# Terminal B — OEM (consumer)
cd deployment/reed-dataspace
./scripts/run-backend.sh oem             # -> http://localhost:9001/docs
```

On startup each backend logs `[REED] Metadata tables ensured: ...` — the five REED
tables are created automatically in that participant's database. Connector/DTR
"START UP ERROR" warnings are **expected and harmless** here: REED's classification,
policy, authorization, access-request and audit features do not need EDC/DTR. (You
add those in §8.)

Verify both are live:

```bash
curl -s http://localhost:9000/v1/reed/classification   # [] until seeded
curl -s http://localhost:9001/v1/reed/classification
```

> **Why no token?** These tutorial backends run with `authorization.enabled: false`.
> With auth off, REED treats every caller as a trusted **service principal** (it gets
> the `reed-admin` capability). This is the same trust model the production code uses
> for the API-key path — see [README.md](README.md) §1.4. You switch on per-user
> Keycloak identity in §9.

---

## 5. Step 3 — Seed the policy catalogue & classification matrix

```bash
cd deployment/reed-dataspace
./scripts/seed.sh
```

This calls `POST /reed/admin/seed` on **both** participants (loading the 8 REED
policy templates + 8 data classifications) and declares the supplier↔OEM
supply-chain relationship on the supplier (the data owner). Expected output:

```
{"templates_created":8,"classifications_created":8}   # supplier
{"templates_created":8,"classifications_created":8}   # OEM
{... "relationType":"supplies_to" ...}                # relation
```

Inspect the supplier's matrix:

```bash
curl -s http://localhost:9000/v1/reed/classification | jq '.[] | {assetClass, sensitivity, discoverability, defaultPolicyTemplate}'
```

---

## 6. Step 4 — Run the end-to-end exchange

```bash
cd deployment/reed-dataspace
./scripts/demo-exchange.sh
```

The script walks the full REED MVP flow against the supplier (the data owner),
and prints each step:

1. **Classify** — list the supplier's data classification matrix.
2. **Policy** — render the `oem-only` contract policy to **EDC/ODRL** JSON.
3. **Authorize** — the OEM asks "may I access `ProcessCapability`?" → the
   context-based engine answers `allowed: true`, `matchedPolicyTemplate: oem-only`,
   `requiredObligations: [audit]` (because there is a supply-chain relation, an
   active NDA, a framework agreement, and a permitted purpose).
4. **Request** — the OEM submits an access request.
5. **Decide** — the supplier approves it.
6. **Contract** — record the (simulated) EDC agreement + transfer IDs.
7. **Audit** — read the three audit events (`access_requested`, `access_approved`,
   `data_transferred`) with participant, BPN, policy and outcome.

Try a **denial**: re-run step 3 with `"ndaActive": false` and watch REED refuse —
`confidential data requires an active NDA`:

```bash
curl -s -X POST http://localhost:9000/v1/reed/authorization/evaluate \
  -H "content-type: application/json" \
  -d '{"bpn":"BPNLREEDOEM00001","ownerBpn":"BPNLREEDSUPP0001","assetClass":"ProcessCapability",
       "usagePurpose":"reed.supply-chain.planning:1","membershipActive":true,
       "frameworkAgreement":"DataExchangeGovernance:1.0","ndaActive":false}' | jq
```

This is the core REED lesson: **identity + context + classification + policy →
decision**, evaluated before any cross-company call, and always audited.

---

## 7. Step 5 — Explore it in the portal (optional)

Start each participant's portal in two more terminals:

```bash
./scripts/run-frontend.sh supplier     # http://localhost:5173
./scripts/run-frontend.sh oem          # http://localhost:5174
```

Open the portal, and in the **Add Features** panel enable the
**REED Manufacturing Data Space** kit. You get five screens backed by the same APIs:

- **Data Classification** — the matrix, with a "Seed defaults" button.
- **Policy Templates** — cards per template, "View ODRL" shows the rendered policy.
- **Access Requests** — submit, approve/reject the workflow.
- **Authorization Simulator** — the evaluate form (allow/deny with reasons).
- **Audit Trail** — the activity log.

---

## 8. Managing the dataspace

| Action | Command |
| --- | --- |
| Tail a backend log | watch the terminal, or run with `> file.log 2>&1 &` |
| Inspect a database | pgAdmin (http://localhost:5051) or `docker exec -it reed_postgres psql -U reed -d reed_supplier` |
| List REED tables | `\dt public.reed_*` inside psql |
| Reset a participant's data | `docker exec reed_postgres psql -U reed -c "DROP DATABASE reed_supplier;" && ... CREATE DATABASE` then restart the backend |
| Stop backends/portals | `Ctrl-C` in each terminal |
| Stop infra (keep data) | `./scripts/down.sh` |
| Stop infra + wipe data | `./scripts/down.sh --purge` |

---

## 9. Going secured (per-user identity with Keycloak)

The tutorial path uses a trusted service principal. To exercise the **token-based**
identity model (where the caller's BPN/roles/projects come from a validated JWT and
cannot be spoofed):

1. Start infra with Keycloak: `./scripts/up-infra.sh --secured` (realm `REED` is
   imported from `realm/reed-realm.json` — add your clients, the roles
   `reed-admin` / `oem-manager` / `supplier-owner`, and a `bpn` token-claim mapper).
2. In `config/reed-supplier.yml` / `reed-oem.yml` set `authorization.enabled: true`
   and `authorization.keycloak.enabled: true`.
3. Restart the backends. Now `/reed/*` requires a bearer token (or the API key), and
   `reed_security.get_reed_principal` derives identity from the token. Admin/write
   endpoints require the `reed-admin` role; access-request decisions are restricted
   to the data owner; audit is filtered to your own BPN. See [README.md](README.md)
   §1.4 for the full trust model.

---

## 10. Going sovereign (real EDC + DTR exchange)

REED today owns the *decision and policy* layer; step 6 records a **simulated** EDC
agreement. To make the cross-company transfer real, add the lower connector layer:

- Deploy **Tractus-X EDC** control/data planes, **DTR**, a **submodel service** and
  **Vault** for each participant — via the Tractus-X **Umbrella** chart (see
  [`docs/umbrella/umbrella-deployment-guide.md`](../umbrella/umbrella-deployment-guide.md))
  or the [MXD tutorial](https://github.com/eclipse-tractusx/tutorial-resources/tree/main/mxd).
- Point each participant's `consumer`/`provider` blocks in its config at its EDC/DTR.
- Extend the access-request `contract` step to call the EDC management API, using the
  ODRL body that `GET /reed/policy-templates/{name}/odrl` already produces.

At that point REED publishes only discoverable metadata to DTR/EDC, negotiates the
contract through EDC under the REED policy template, transfers the payload through the
EDC data plane, and records the **real** agreement/transfer IDs in the audit trail —
the complete sovereign flow from the
[architecture document](../architecture/reed-manufacturing-data-space.md).

---

## 11. Troubleshooting

| Symptom | Fix |
| --- | --- |
| Backend loops on `Database not ready ... port 5433` | Infra isn't up. Run `./scripts/up-infra.sh` first. |
| `Connection refused ... :8080` at startup | Expected when Keycloak isn't running and auth is disabled — harmless. |
| `port is already allocated` | Another stack uses 5433/9000/5173. Stop it or edit the ports. |
| Seed returns 403 | Auth is enabled but you didn't send a `reed-admin` token/API key. |
| `[]` everywhere | You haven't run `./scripts/seed.sh`. |
| Portal can't reach backend | Check `VITE_ICHUB_BACKEND_URL` (set by `run-frontend.sh`) and CORS origins in the config. |
