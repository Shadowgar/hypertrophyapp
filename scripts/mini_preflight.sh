#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

required_files=(
  "docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md"
  "docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md"
  "docs/archive/ai-handoffs/GPT5_MINI_RUNBOOK.md"
  "docs/archive/ai-handoffs/GPT5_MINI_SUCCESS_PLAN.md"
  "docs/Master_Plan.md"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[FAIL] Missing required file: $file"
    exit 1
  fi
  echo "[OK] $file"
done

echo "[CHECK] Master plan audit evidence paths"
"$ROOT/scripts/verify_master_plan_audit.sh"

echo "[PASS] Mini preflight checks complete. Mini is clear for full-scope implementation work."
