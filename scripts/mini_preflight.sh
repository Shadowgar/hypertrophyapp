#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

required_files=(
  "docs/GPT5_MINI_HANDOFF.md"
  "docs/GPT5_MINI_EXECUTION_BACKLOG.md"
  "docs/GPT5_MINI_RUNBOOK.md"
  "docs/Master_Plan.md"
  "apps/api/app/routers/plan.py"
  "apps/api/app/routers/profile.py"
  "apps/api/app/program_loader.py"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[FAIL] Missing required file: $file"
    exit 1
  fi
  echo "[OK] $file"
done

if ! grep -q 'GET /plan/programs' docs/GPT5_MINI_HANDOFF.md; then
  echo "[FAIL] Handoff doc missing /plan/programs contract"
  exit 1
fi

if ! grep -q 'Model Ownership & Quality Routing' docs/Master_Plan.md; then
  echo "[FAIL] Master Plan missing model ownership section"
  exit 1
fi

echo "[PASS] Mini preflight checks complete. Safe to continue with mini backlog tasks."
