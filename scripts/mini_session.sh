#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[mini-session] preflight"
./scripts/mini_preflight.sh

echo "[mini-session] next backlog task"
NEXT_TASK="$(awk '/^### Task/{task=$0} /^ Status:/{if($0 !~ /COMPLETED/){print task; exit}}' docs/GPT5_MINI_EXECUTION_BACKLOG.md || true)"
if [[ -n "${NEXT_TASK:-}" ]]; then
  echo "$NEXT_TASK"
else
  echo "No incomplete task found in docs/GPT5_MINI_EXECUTION_BACKLOG.md"
fi

echo "[mini-session] validation"
./scripts/mini_validate.sh

echo "[mini-session] done"
