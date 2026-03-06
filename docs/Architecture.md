# Architecture

## Runtime Services
- `apps/web`: Next.js App Router client, mobile-first UI + PWA shell.
- `apps/api`: FastAPI service exposing auth/profile/planning/logging endpoints.
- `postgres`: primary datastore for users, plans, logs, state.
- `caddy`: reverse proxy routing `/api/*` to API and all other routes to web.

## Deterministic Runtime Constraint
- Runtime only reads persisted DB state + canonical templates in `programs/`.
- Runtime does not parse `reference/` assets and does not perform search retrieval.
- Build-time import pipeline (`importers/`) produces canonical templates.

## Data Model Overview
- `users`: account + onboarding profile + nutrition settings + equipment context (`training_location`, `equipment_profile`).
- `weekly_checkins`: weekly adherence and bodyweight snapshots.
- `workout_plans`: generated weekly plan payloads by template/version.
- `workout_set_logs`: per-set logs from runner with slot continuity (`primary_exercise_id`) and performed movement (`exercise_id`).
- `exercise_states`: progression state per user/exercise.

## Core Engine Services
- Warmup service: deterministic ramp sets from target working weight.
- Progression service: next load recommendation from reps/sets/phase modifier.
- State update service: updates exposure/fatigue/next load after logging.
- Scheduler service: generates week sessions from templates, availability, and equipment constraints.

## Deployment Topology (Raspberry Pi)
- Single-node Docker Compose deployment.
- Caddy exposes port `80` for LAN access.
- API and web run internally; Postgres not exposed externally by default.
- Data durability via Docker volume + backup script in `infra/scripts`.

## Configuration
- `.env` controls DB URL, JWT settings, and web API base URL.
- `PROGRAMS_DIR` points API to canonical template directory.

## Scaling Notes
- MVP is single-node local-first.
- Horizontal scaling can be introduced later by externalizing Postgres and using sticky auth/session policy.

## Progress Sync (2026-03-06)
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

