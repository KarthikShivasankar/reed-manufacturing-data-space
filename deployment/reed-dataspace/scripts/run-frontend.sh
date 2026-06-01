#!/usr/bin/env bash
###############################################################
# Eclipse Tractus-X - Industry Core Hub
# Copyright (c) 2026 Contributors to the Eclipse Foundation
# SPDX-License-Identifier: Apache-2.0
###############################################################
#
# Run a REED participant frontend from source (Vite dev server).
# Usage: ./run-frontend.sh <supplier|oem>
#
#   supplier -> http://localhost:5173, talks to backend :9000
#   oem      -> http://localhost:5174, talks to backend :9001
set -euo pipefail

ROLE="${1:-}"
case "$ROLE" in
  supplier) PORT=5173; BACKEND_URL="http://localhost:9000/v1"; BPN="BPNLREEDSUPP0001" ;;
  oem)      PORT=5174; BACKEND_URL="http://localhost:9001/v1"; BPN="BPNLREEDOEM00001" ;;
  *) echo "Usage: $0 <supplier|oem>"; exit 1 ;;
esac

REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
FRONTEND="$REPO/ichub-frontend"
cd "$FRONTEND"

if [[ ! -d node_modules ]]; then
  echo "[REED] Installing frontend dependencies (first run only)..."
  npm install --no-audit --no-fund
fi

echo "[REED] Starting $ROLE frontend on http://localhost:$PORT -> backend $BACKEND_URL"
exec env VITE_ICHUB_BACKEND_URL="$BACKEND_URL" VITE_PARTICIPANT_ID="$BPN" \
  npx vite --port "$PORT" --strictPort
