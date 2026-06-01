#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Seed both REED participants with the default policy catalogue + classification
# matrix, and declare the supplier<->OEM supply-chain relationship on the
# supplier (data owner) instance.
set -euo pipefail

SUPPLIER="${SUPPLIER_URL:-http://localhost:9000/v1}"
OEM="${OEM_URL:-http://localhost:9001/v1}"
SUP_BPN="BPNLREEDSUPP0001"
OEM_BPN="BPNLREEDOEM00001"

echo "[REED] Seeding defaults on supplier ($SUPPLIER)..."
curl -fsS -X POST "$SUPPLIER/reed/admin/seed" | sed 's/^/   /'
echo
echo "[REED] Seeding defaults on OEM ($OEM)..."
curl -fsS -X POST "$OEM/reed/admin/seed" | sed 's/^/   /'
echo
echo "[REED] Declaring supply-chain relation (OEM <- supplier) on supplier..."
curl -fsS -X POST "$SUPPLIER/reed/supply-chain/relations" \
  -H "content-type: application/json" \
  -d "{\"parentBpn\":\"$OEM_BPN\",\"childBpn\":\"$SUP_BPN\",\"relationType\":\"supplies_to\",\"project\":\"reed-pilot\"}" \
  | sed 's/^/   /' || echo "   (relation may already exist)"
echo
echo "[REED] Seed complete."
