#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT/apps/web"

cd "$WEB_DIR"
echo "[1/2] Building web app for performance metrics"
npm run build

echo "[2/2] Running mobile bundle and route budget checks"
node "$ROOT/scripts/mobile_perf_check.mjs"

echo "[PASS] Mobile performance validation complete."
