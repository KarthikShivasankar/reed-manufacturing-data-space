#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Tear down the REED dataspace infrastructure.
# Usage: ./down.sh [--purge]   (--purge also deletes the Postgres volume)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--purge" ]]; then
  echo "[REED] Stopping infrastructure and DELETING data volume..."
  docker compose --profile secured down -v
else
  echo "[REED] Stopping infrastructure (data volume preserved)..."
  docker compose --profile secured down
fi

echo "[REED] Note: stop the backends/frontends in their own terminals (Ctrl-C)."
