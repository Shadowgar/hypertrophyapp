#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/3] API regression tests"
# Run full API test suite in a freshly built container if available, otherwise run locally with PYTHONPATH set
if command -v docker >/dev/null 2>&1 && (docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1); then
	echo "- running pytest in fresh api container (docker compose available)"
	if docker compose version >/dev/null 2>&1; then
		COMPOSE_CMD=(docker compose)
	else
		COMPOSE_CMD=(docker-compose)
	fi

	if ! "${COMPOSE_CMD[@]}" run --rm --build api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests -q'; then
		echo "- initial containerized API test run failed; rebuilding api image with --no-cache and retrying once"
		"${COMPOSE_CMD[@]}" build --no-cache api
		"${COMPOSE_CMD[@]}" run --rm api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests -q'
	fi
else
	echo "- docker compose not available; running pytest locally with PYTHONPATH=."
	(cd "$ROOT/apps/api" && PYTHONPATH=. pytest tests -q)
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
