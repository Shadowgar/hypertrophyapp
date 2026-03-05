#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="${POSTGRES_DB:-hypertrophy}"
DB_USER="${POSTGRES_USER:-hypertrophy}"

printf 'Resetting user/testing data in database "%s"...\n' "$DB_NAME"

docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" <<'SQL'
TRUNCATE TABLE
  workout_set_logs,
  workout_plans,
  weekly_review_cycles,
  exercise_states,
  weekly_checkins,
  soreness_entries,
  body_measurement_entries,
  password_reset_tokens,
  users
RESTART IDENTITY CASCADE;
SQL

printf 'Done. User/testing data wiped; onboarding can be re-run from scratch.\n'
