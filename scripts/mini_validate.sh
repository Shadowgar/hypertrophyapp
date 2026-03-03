#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/3] API regression tests"
# Try running tests inside API container if docker compose available, otherwise run locally with PYTHONPATH set
if command -v docker >/dev/null 2>&1 && (docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1); then
	echo "- running pytest inside api container (docker compose available)"
	if docker compose ps >/dev/null 2>&1; then
		docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py tests/test_workout_progress.py tests/test_program_loader.py -q'
	else
		echo "- docker compose present but services not running; attempting local pytest fallback"
		(cd "$ROOT/apps/api" && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py tests/test_workout_progress.py tests/test_program_loader.py -q)
	fi
else
	echo "- docker compose not available; running pytest locally with PYTHONPATH=."
	(cd "$ROOT/apps/api" && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py tests/test_workout_progress.py tests/test_program_loader.py -q)
fi

echo "[2/4] Web tests"
cd "$ROOT/apps/web"
npm run test --silent

echo "[3/4] Web build"
cd "$ROOT/apps/web"
npm run build

cd "$ROOT"
echo "[4/4] Changed files overview"
git --no-pager status --short

echo "[PASS] Mini validation complete."
