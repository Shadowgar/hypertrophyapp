#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/3] API regression tests"
docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py tests/test_program_loader.py -q'

echo "[2/3] Web build"
cd "$ROOT/apps/web"
npm run build

cd "$ROOT"
echo "[3/3] Changed files overview"
git --no-pager status --short

echo "[PASS] Mini validation complete."
