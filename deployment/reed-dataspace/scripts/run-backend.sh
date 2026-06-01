#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Run a REED participant backend from source.
# Usage: ./run-backend.sh <supplier|oem>
#
#   supplier -> port 9000, config/reed-supplier.yml, db reed_supplier
#   oem      -> port 9001, config/reed-oem.yml,      db reed_oem
set -euo pipefail

ROLE="${1:-}"
case "$ROLE" in
  supplier) PORT=9000; CFG="reed-supplier.yml" ;;
  oem)      PORT=9001; CFG="reed-oem.yml" ;;
  *) echo "Usage: $0 <supplier|oem>"; exit 1 ;;
esac

HERE="$(cd "$(dirname "$0")/.." && pwd)"          # deployment/reed-dataspace
REPO="$(cd "$HERE/../.." && pwd)"                  # repo root
BACKEND="$REPO/ichub-backend"
CONFIG="$HERE/config/$CFG"

# Create / reuse a virtualenv for the backend.
VENV="$REPO/.reed-venv"
if [[ ! -d "$VENV" ]]; then
  echo "[REED] Creating virtualenv at $VENV ..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt"
fi

echo "[REED] Starting $ROLE backend on http://localhost:$PORT (config: $CFG)"
echo "[REED] Swagger UI: http://localhost:$PORT/docs"
cd "$BACKEND"
exec "$VENV/bin/python" main.py --config "$CONFIG" --host 0.0.0.0 --port "$PORT"
