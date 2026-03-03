#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[mini-session] preflight"
./scripts/mini_preflight.sh

echo "[mini-session] next backlog task"
./scripts/mini_next_task.sh

echo "[mini-session] validation"
./scripts/mini_validate.sh

echo "[mini-session] done"
