#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Start the REED dataspace shared infrastructure (Postgres + pgAdmin).
# Usage: ./up-infra.sh [--secured]   (--secured also starts Keycloak)
set -euo pipefail
cd "$(dirname "$0")/.."

PROFILE_ARGS=()
if [[ "${1:-}" == "--secured" ]]; then
  PROFILE_ARGS=(--profile secured)
  echo "[REED] Starting infrastructure WITH Keycloak (secured profile)..."
else
  echo "[REED] Starting infrastructure (Postgres + pgAdmin)..."
fi

docker compose "${PROFILE_ARGS[@]}" up -d

echo "[REED] Waiting for Postgres to become healthy..."
until docker exec reed_postgres pg_isready -U reed >/dev/null 2>&1; do
  sleep 2
done
echo "[REED] Infrastructure ready."
echo "       Postgres : localhost:5433 (user=reed, pass=reed, dbs=reed_supplier/reed_oem)"
echo "       pgAdmin  : http://localhost:5051 (admin@reed.local / admin)"
if [[ "${1:-}" == "--secured" ]]; then
  echo "       Keycloak : http://localhost:8080 (admin / admin), realm=REED"
fi
