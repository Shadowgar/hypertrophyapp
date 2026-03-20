#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

API_TESTS=(
  tests/test_plan_guides_api.py
  tests/test_program_recommendation_and_switch.py
  tests/test_weekly_review.py
  tests/test_reference_corpus_ingestion.py
  tests/test_runtime_source_boundaries.py
  tests/test_source_registry_contract.py
  tests/test_source_to_knowledge_pipeline.py
  tests/test_exercise_library_contract.py
  tests/test_knowledge_loader.py
)

WEB_TESTS=(
  tests/guides.phase.test.tsx
  tests/settings.program.test.tsx
  tests/week.program.test.tsx
  tests/onboarding.program.test.tsx
  tests/today.runner.test.tsx
  tests/today.logset.test.tsx
  tests/today.substitution.test.tsx
)

echo "[1/2] API deterministic regression checks"
if command -v docker >/dev/null 2>&1 && (docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1); then
  echo "- running focused API tests in docker compose api service"
  docker compose run --rm --build api sh -lc "cd /app/apps/api && PYTHONPATH=. pytest ${API_TESTS[*]} -q"
else
  echo "- docker compose not available; running focused API tests locally"
  API_PYTHON="$ROOT/apps/api/.venv/bin/python"
  FALLBACK_PYTHON="$(command -v python3 || true)"
  SQLITE_TEST_DB="$ROOT/apps/api/.tmp_deterministic_regression.sqlite3"
  CREATED_SQLITE_FALLBACK=0
  (
    cd "$ROOT/apps/api"
    if [ -z "${TEST_DATABASE_URL:-}" ]; then
      if command -v pg_isready >/dev/null 2>&1 && pg_isready -h "${TEST_DATABASE_HOST:-localhost}" -p "${TEST_DATABASE_PORT:-5432}" >/dev/null 2>&1; then
        echo "- using available local Postgres test database"
      else
        echo "- local Postgres unavailable; using deterministic SQLite fallback at $SQLITE_TEST_DB"
        rm -f "$SQLITE_TEST_DB"
        export TEST_DATABASE_URL="sqlite:///$SQLITE_TEST_DB"
        CREATED_SQLITE_FALLBACK=1
      fi
    fi

    if command -v pytest >/dev/null 2>&1; then
      PYTHONPATH=. pytest "${API_TESTS[@]}" -q
    elif [ -x "$API_PYTHON" ]; then
      PYTHONPATH=. "$API_PYTHON" -m pytest "${API_TESTS[@]}" -q
    elif [ -n "$FALLBACK_PYTHON" ]; then
      PYTHONPATH=. "$FALLBACK_PYTHON" -m pytest "${API_TESTS[@]}" -q
    else
      echo "pytest is unavailable and no Python fallback was found" >&2
      exit 1
    fi

    if [ "$CREATED_SQLITE_FALLBACK" -eq 1 ]; then
      rm -f "$SQLITE_TEST_DB"
    fi
  )
fi

echo "[2/2] Web deterministic regression checks"
(
  cd "$ROOT/apps/web"
  npm run test --silent -- "${WEB_TESTS[@]}"
)

echo "[PASS] Deterministic behavior regression validation complete."
