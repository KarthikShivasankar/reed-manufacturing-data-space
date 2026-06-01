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

# REED Manufacturing Data Space — Backend Module

This module implements the REED Manufacturing Data Space layer **on top of** the
Industry Core Hub (ICH) backend. It is the T5.4 build of the design captured in
[`docs/architecture/reed-manufacturing-data-space.md`](../architecture/reed-manufacturing-data-space.md).

REED does **not** re-implement a connector, registry, identity system or policy
engine. It adds a thin use-case layer that owns:

- the **data classification matrix** (DMP-derived),
- the **policy catalogue** (catalogue / contract / usage templates) and their
  rendering into EDC/ODRL,
- the **supply-chain relationship graph**,
- the **context-based authorization engine** that runs before any EDC/DTR call,
- the **access-request workflow**, and
- the **audit trail**.

EDC still owns inter-company contract negotiation and transfer, DTR owns digital
twin discoverability, and Keycloak owns identity — exactly as in stock ICH.

---

## 1. Concepts

### 1.1 Asset classes
REED models eight manufacturing asset types as `ReedAssetClass`: `PartDigitalTwin`,
`BillOfMaterial`, `DigitalProductPassport`, `ProcessCapability`,
`FixtureHandlingStrategy`, `ProductionStatus`, `QualityEvidence`,
`SimulationResult`. Each maps to an AAS submodel `semanticId`.

### 1.2 Data classification matrix
Each asset class has one `ReedAssetClassification` entry describing:

| Field | Meaning |
| --- | --- |
| `sensitivity` | `public` → `consortium` → `restricted` → `confidential` → `regulated` |
| `discoverability` | who can see the metadata exists: `public`/`consortium`/`project`/`bilateral`/`hidden` |
| `payloadStorage` | where the confidential payload lives (submodel service, object store, …) |
| `defaultPolicyTemplate` | the policy applied when an EDC asset of this class is published |
| `allowedPurposes` | the usage purposes a consumer may declare |
| `obligations` / `prohibitions` | duties/limits attached to the data |

Only **metadata** is published to DTR/EDC catalogues; the payload stays in the
submodel service until a contract is accepted.

### 1.3 Three policy layers
Mirroring Task 5.3, every `ReedPolicyTemplate` belongs to one `ReedPolicyLayer`:

- **catalogue** — *can a partner discover that metadata exists?*
- **contract** — *can a partner negotiate access?* (expressed in EDC/ODRL)
- **usage** — *obligations & prohibitions attached to the data.*

A template stores abstract `{leftOperand, operator, rightOperand}` constraints.
`PolicyTemplateService.render_entity()` turns them into an EDC-ready ODRL policy
definition using the standard `cx-policy` / `odrl` / `edc` JSON-LD context.

### 1.4 Context-based authorization
`AuthorizationService.authorize(ctx)` is the heart of REED. It combines:

- **identity claims** (from the Keycloak token): `bpn`, `roles`, `projects`,
  `membershipActive`, `frameworkAgreement`, `ndaActive`;
- **request context**: `ownerBpn`, `assetClass`, `usagePurpose`, `project`;
- **REED state**: the classification entry + the supply-chain graph.

It returns an `allowed` decision, human-readable `reasons`, the
`matchedPolicyTemplate` that would govern the EDC contract, and the
`requiredObligations`. Decision rules (in order):

1. Owner accessing own data → allow.
2. `reed-admin` role → allow (break-glass).
3. No classification for the asset class → **deny** (default-deny).
4. Discoverability gate (`hidden` deny; `consortium` needs membership;
   `project` needs project membership; `bilateral` needs a supply-chain edge).
5. `confidential`/`regulated` sensitivity additionally needs an active NDA **and**
   an accepted framework agreement.
6. Purpose binding: the declared `usagePurpose` must be in `allowedPurposes`.

This is deliberately deterministic and side-effect-free so it is easy to unit
test; the API layer records denials to the audit log.

### 1.5 Access-request workflow
`ReedAccessRequest` moves through:
`submitted → under_review → approved/rejected → contracted → transferred`
(`expired`/`revoked` are terminal). Every transition writes a `ReedAuditEvent`.

---

## 2. Where the code lives

| Concern | Path |
| --- | --- |
| DB models + enums | `ichub-backend/models/metadata_database/reed/models.py` |
| Table bootstrap | `ichub-backend/models/metadata_database/reed/tables.py` |
| API schemas | `ichub-backend/models/services/reed/*.py` |
| Repositories | `ichub-backend/managers/metadata_database/reed_repositories.py` |
| Repository wiring | `ichub-backend/managers/metadata_database/manager.py` |
| Services (business logic) | `ichub-backend/services/reed/*.py` |
| FastAPI routers | `ichub-backend/controllers/fastapi/routers/reed/v1/*.py` |
| App registration + startup | `ichub-backend/controllers/fastapi/app.py` |
| Reference DDL (optional) | `docs/database/REED-DDL-public.sql` |
| Tests | `ichub-backend/tests/services/reed/*.py` |

All endpoints are mounted under `/<API_V1>/reed/...` (default `/v1/reed/...`) and
inherit the existing API-key / Keycloak authentication dependency.

---

## 3. API reference

All paths are relative to the API root (e.g. `http://localhost:8000/v1`).

### Data classification — `/reed/classification`
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/reed/classification` | List the classification matrix |
| GET | `/reed/classification/{assetClass}` | Get one entry |
| POST | `/reed/classification` | Create an entry |
| PATCH | `/reed/classification/{assetClass}` | Update an entry |

### Policy templates — `/reed/policy-templates`
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/reed/policy-templates?layer=` | List templates (optionally by layer) |
| GET | `/reed/policy-templates/{name}` | Get a template |
| GET | `/reed/policy-templates/{name}/odrl` | **Render** the template to EDC/ODRL |
| POST | `/reed/policy-templates` | Create a template |
| DELETE | `/reed/policy-templates/{name}` | Delete a non-builtin template |

### Supply chain — `/reed/supply-chain`
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/reed/supply-chain/relations` | List all relations |
| GET | `/reed/supply-chain/relations/{bpn}` | Relations touching a BPN |
| POST | `/reed/supply-chain/relations` | Create a relation edge |

### Authorization — `/reed/authorization`
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/reed/authorization/evaluate` | Evaluate a context-based decision |

### Access requests — `/reed/access-requests`
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/reed/access-requests` | Submit a request |
| GET | `/reed/access-requests` | List (filter by `ownerBpn`, `requestingBpn`, `status`) |
| GET | `/reed/access-requests/{requestId}` | Get one |
| POST | `/reed/access-requests/{requestId}/decision` | Approve / reject |
| POST | `/reed/access-requests/{requestId}/contract?edcAgreementId=&edcTransferId=` | Record EDC agreement / transfer |

### Audit — `/reed/audit`
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/reed/audit/events` | Query the audit trail |

### Administration — `/reed/admin`
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/reed/admin/seed?overwrite=` | Seed the default policy catalogue + classification matrix |

---

## 4. MVP walk-through (curl)

> Set `KEY` to your API key header value. If `authorization.enabled` is false in
> your config, you can omit the header entirely.

```shell
API=http://localhost:8000/v1
H="x-api-key: $KEY"

# 0. One-time: seed the default policy catalogue + classification matrix.
curl -s -X POST "$API/reed/admin/seed" -H "$H" | jq

# 1. Inspect the DMP-derived classification matrix.
curl -s "$API/reed/classification" -H "$H" | jq

# 2. See how a contract policy renders to EDC/ODRL.
curl -s "$API/reed/policy-templates/simulation-service-only/odrl" -H "$H" | jq

# 3. Declare a supply-chain relationship (OEM <- supplier).
curl -s -X POST "$API/reed/supply-chain/relations" -H "$H" -H "content-type: application/json" -d '{
  "parentBpn": "BPNL000000000OEM", "childBpn": "BPNL0000000SUPPLIER",
  "relationType": "supplies_to", "project": "reed-pilot"
}' | jq

# 4. Authorize a consumer BEFORE touching EDC/DTR.
curl -s -X POST "$API/reed/authorization/evaluate" -H "$H" -H "content-type: application/json" -d '{
  "bpn": "BPNL000000000OEM", "ownerBpn": "BPNL0000000SUPPLIER",
  "assetClass": "ProcessCapability", "usagePurpose": "reed.supply-chain.planning:1",
  "membershipActive": true, "frameworkAgreement": "DataExchangeGovernance:1.0",
  "ndaActive": true, "project": "reed-pilot", "projects": ["reed-pilot"]
}' | jq
# -> { "allowed": true, "matchedPolicyTemplate": "oem-only", "requiredObligations": ["audit"] }

# 5. Submit an access request.
REQ=$(curl -s -X POST "$API/reed/access-requests" -H "$H" -H "content-type: application/json" -d '{
  "requestingBpn": "BPNL000000000OEM", "ownerBpn": "BPNL0000000SUPPLIER",
  "assetClass": "ProcessCapability", "usagePurpose": "reed.supply-chain.planning:1",
  "project": "reed-pilot", "requestingUser": "alice"
}')
ID=$(echo "$REQ" | jq -r .requestId)

# 6. Provider approves.
curl -s -X POST "$API/reed/access-requests/$ID/decision" -H "$H" -H "content-type: application/json" -d '{
  "approve": true, "reason": "Active supplier in reed-pilot", "decidedBy": "bob"
}' | jq

# 7. After EDC negotiation/transfer, record the agreement + transfer.
curl -s -X POST "$API/reed/access-requests/$ID/contract?edcAgreementId=agr-123&edcTransferId=tr-456" -H "$H" | jq

# 8. Read the audit trail for the request.
curl -s "$API/reed/audit/events?accessRequestId=$ID" -H "$H" | jq
```

This exercises the full MVP flow from the architecture document: classify →
policy → authorize → request → decide → contract/transfer → audit.

---

## 5. Running it

> **Want your own dataspace?** The fastest way to see REED end to end is the
> two-participant local data space (REED-Supplier + REED-OEM), an MXD-style
> tutorial that is **not** Catena-X: see
> [`REED-DATASPACE-TUTORIAL.md`](REED-DATASPACE-TUTORIAL.md) and
> [`deployment/reed-dataspace/`](../../deployment/reed-dataspace).

See the repository [QUICKSTART](../QUICKSTART.md) and [INSTALL](../../INSTALL.md)
for the full ICH setup. The REED module needs nothing beyond a running ICH
backend + PostgreSQL.

### Local (Python)
```shell
cd ichub-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point configuration.yaml at your PostgreSQL (database.connection_string)
python main.py --config ./config/configuration.yaml
```
On startup the backend logs `[REED] Metadata tables ensured: ...` — the five
REED tables are created automatically (only if missing). Then seed defaults:
```shell
curl -X POST http://localhost:8000/v1/reed/admin/seed
```
Open Swagger UI at `http://localhost:8000/docs` — the REED endpoints appear under
the **REED Manufacturing Data Space** tag group.

### Kubernetes / Helm
No chart changes are required: REED ships inside the backend image and creates
its tables on startup (the backend DB user already has DDL rights in the standard
chart). After deploy, call `POST /v1/reed/admin/seed` once. If your operator
provisions the schema out-of-band, apply
[`docs/database/REED-DDL-public.sql`](../database/REED-DDL-public.sql) instead and
the startup hook becomes a no-op.

---

## 6. Tests

```shell
cd ichub-backend
python -m pytest tests/services/reed/ -q
```
Covers the ODRL rendering and every branch of the authorization engine
(owner/admin bypass, default-deny, discoverability gates, NDA/framework
escalation, purpose binding).

---

## 7. How REED uses the rest of the stack

```
Caller ─▶ REED API ─▶ AuthorizationService (token claims + classification + graph)
                         │ allow
                         ▼
                 PolicyTemplateService ──▶ EDC management API (asset, policy, contractdef)
                 DTR (AAS shell + submodel descriptors)
                 Submodel service (confidential payload, post-contract)
                         │
                         ▼
                 AuditService (who/what/why/when/outcome)
```

The EDC/DTR/submodel calls themselves reuse the existing ICH connector and DTR
managers; REED supplies the *decisions* and *policies* that drive them. Wiring
the access-request `contract` step to an actual EDC contract-definition call is
the natural next increment (the rendered ODRL from `PolicyTemplateService` is the
exact body the EDC management API expects).
