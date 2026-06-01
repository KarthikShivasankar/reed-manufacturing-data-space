#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Walk through the full REED MVP data-exchange flow between two participants:
#   classify -> authorize -> request -> decide -> contract -> audit
#
# Everything is driven against the SUPPLIER (data owner) instance, which is where
# the access-request workflow and audit trail live. The OEM is the consumer.
# Requires: the dataspace running (infra + both backends) and seed.sh already run.
set -euo pipefail

SUPPLIER="${SUPPLIER_URL:-http://localhost:9000/v1}"
SUP_BPN="BPNLREEDSUPP0001"
OEM_BPN="BPNLREEDOEM00001"
JQ() { if command -v jq >/dev/null 2>&1; then jq "$@"; else cat; fi; }

echo "=============================================================="
echo " STEP 1 — Inspect the supplier's data classification matrix"
echo "=============================================================="
curl -fsS "$SUPPLIER/reed/classification" | JQ '.[] | {assetClass, sensitivity, discoverability, defaultPolicyTemplate}'

echo; echo "=============================================================="
echo " STEP 2 — Render the contract policy that will govern the deal"
echo "=============================================================="
curl -fsS "$SUPPLIER/reed/policy-templates/oem-only/odrl" | JQ '.odrl.policy'

echo; echo "=============================================================="
echo " STEP 3 — OEM asks: am I authorized to access ProcessCapability?"
echo "=============================================================="
curl -fsS -X POST "$SUPPLIER/reed/authorization/evaluate" \
  -H "content-type: application/json" \
  -d "{\"bpn\":\"$OEM_BPN\",\"ownerBpn\":\"$SUP_BPN\",\"assetClass\":\"ProcessCapability\",
       \"usagePurpose\":\"reed.supply-chain.planning:1\",\"project\":\"reed-pilot\",\"projects\":[\"reed-pilot\"],
       \"membershipActive\":true,\"frameworkAgreement\":\"DataExchangeGovernance:1.0\",\"ndaActive\":true}" \
  | JQ '{allowed, matchedPolicyTemplate, requiredObligations, reasons}'

echo; echo "=============================================================="
echo " STEP 4 — OEM submits an access request"
echo "=============================================================="
REQ=$(curl -fsS -X POST "$SUPPLIER/reed/access-requests" \
  -H "content-type: application/json" \
  -d "{\"requestingBpn\":\"$OEM_BPN\",\"ownerBpn\":\"$SUP_BPN\",\"assetClass\":\"ProcessCapability\",
       \"usagePurpose\":\"reed.supply-chain.planning:1\",\"project\":\"reed-pilot\",\"requestingUser\":\"oem-buyer\"}")
echo "$REQ" | JQ '{requestId, status, policyTemplate}'
RID=$(echo "$REQ" | (command -v jq >/dev/null 2>&1 && jq -r .requestId || sed -n 's/.*"requestId":"\([^"]*\)".*/\1/p'))
echo "   request id = $RID"

echo; echo "=============================================================="
echo " STEP 5 — Supplier approves the request"
echo "=============================================================="
curl -fsS -X POST "$SUPPLIER/reed/access-requests/$RID/decision" \
  -H "content-type: application/json" \
  -d '{"approve":true,"reason":"Active supplier in reed-pilot","decidedBy":"supplier-admin"}' \
  | JQ '{status, decisionReason}'

echo; echo "=============================================================="
echo " STEP 6 — Record the (simulated) EDC contract agreement + transfer"
echo "=============================================================="
curl -fsS -X POST "$SUPPLIER/reed/access-requests/$RID/contract?edcAgreementId=agr-demo-001&edcTransferId=tr-demo-001" \
  | JQ '{status, edcAgreementId, edcTransferId}'

echo; echo "=============================================================="
echo " STEP 7 — Read the audit trail for this request"
echo "=============================================================="
curl -fsS "$SUPPLIER/reed/audit/events?accessRequestId=$RID" \
  | JQ '.[] | {createdAt, action, outcome, actorBpn, ownerBpn, policyTemplate}'

echo; echo "[REED] MVP exchange complete. Open the REED portal to see it in the UI:"
echo "       Supplier: http://localhost:5173   OEM: http://localhost:5174"
