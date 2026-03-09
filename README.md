# Rocco's HyperTrophy Plan Monorepo

Deterministic hypertrophy planner + workout runner for local-first deployment.

## Current Status

- Runtime architecture is deterministic and template-driven.
- Onboarding has a multi-step funnel with profile persistence and first-plan bootstrap.
- Frequency adaptation preview/apply is wired across API + web settings.
- Developer-safe onboarding recovery controls exist for local test loops.
- Calendar training history view is delivered with clickable day drill-down and progression comparison on `/history`.

## Stack

- Web: Next.js (App Router), React, TypeScript, Tailwind, shadcn-style components
- API: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Engine: Python `core-engine` package (deterministic progression/scheduling)
- Infra: Docker Compose, Caddy reverse proxy

## Deterministic Runtime Rules

- Runtime never parses raw `reference/*.pdf` or `reference/*.xlsx`.
- Runtime never depends on `docs/guides/generated/*.md`.
- Program generation uses canonical templates from `programs/` plus persisted user state.
- Adaptation decisions must be explainable and testable.

Reference contracts:
- `docs/Architecture.md`
- `docs/High_Risk_Contracts.md`
- `docs/Canonical_Program_Schema.md`

## Quick Start

1. Install Docker + Docker Compose plugin.
2. Copy env file:
   - `cp .env.example .env`
3. Start services:
   - `docker compose up --build`
4. Open app:
   - `http://<host>:18080/`
5. Check API health:
   - `http://<host>:18080/api/health`

## Local Development Commands

Web:
- `cd apps/web && npm install`
- `cd apps/web && npm run dev`
- `cd apps/web && npm run test`

API:
- `cd apps/api && .venv/bin/pip install -r requirements.txt`
- `cd apps/api && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- `cd apps/api && .venv/bin/pytest tests -q`

Note: this repo often uses direct `.venv/bin/...` commands instead of `source .venv/bin/activate`.

## Database Migrations (Alembic)

- Upgrade schema in container:
  - `docker compose exec api alembic upgrade head`
- Create migration revision:
  - `docker compose exec api alembic revision -m "your_change"`

## API Test Configuration

API tests default to PostgreSQL for runtime parity.

Resolved in order:
- `TEST_DATABASE_HOST` or `DATABASE_HOST` or `POSTGRES_HOST` (default `localhost`)
- `TEST_DATABASE_PORT` or `DATABASE_PORT` (default `5432`)
- `TEST_DATABASE_NAME` or `POSTGRES_DB` (default `hypertrophy_test`)
- `TEST_DATABASE_USER` or `POSTGRES_USER` (default `hypertrophy`)
- `TEST_DATABASE_PASSWORD` or `POSTGRES_PASSWORD` (default `hypertrophy`)

One-off SQLite override:
- `TEST_DATABASE_URL=sqlite:///./test_local.db`

Examples:
- `cd apps/api && .venv/bin/pytest tests -q`
- `cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local.db .venv/bin/pytest tests/test_health.py -q`

## Onboarding/Auth Reliability (Local Testing)

The onboarding screen includes developer recovery controls for test loops:
- `Wipe Test User By Email` -> calls `POST /auth/dev/wipe-user`
- `Wipe Current Logged-In User Data` -> calls `POST /profile/dev/wipe`
- `Request Password Reset Token` -> calls `POST /auth/password-reset/request`

Behavior:
- Wipe endpoints are environment-gated by `allow_dev_wipe_endpoints` in API settings.
- Auth email matching is case-insensitive and whitespace-normalized in register/login/reset/wipe flows.
- Onboarding questionnaire progress is auto-saved to local browser storage and restored on revisit (with `Clear Saved Draft` control).
- These controls are for local/dev environments and should not be enabled for production deployments.

Related docs:
- `docs/Onboarding_and_Flows.md`
- `docs/redesign/Onboarding_Reference_Process_Map.md`
- `docs/Auth_Expansion_Architecture.md`

## History Calendar API (MVP)

- `GET /history/calendar?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
   - Returns day-by-day completion summary (`set_count`, `exercise_count`, `total_volume`), streak context, program/muscle metadata, and PR badge metadata.
- `GET /history/day/{day}`
   - Returns performed workout/exercise/set details and planned-vs-performed set deltas for a selected date when plan data exists.
   - Includes planned-only detail for missed days with scheduled sessions but zero logged sets.

The web history page consumes both endpoints so users can:
- toggle week/month windows and navigate older windows
- filter by completion/program/muscle
- jump to previous same-weekday sessions
- view same-weekday delta cards (sets, volume, PR-day count) for progression comparison
- inspect PR-marked days and missed-day planned details

## Build-Time Reference Corpus Ingestion

Generate deterministic reference artifacts (build-time only):

- `cd apps/api && .venv/bin/pip install -r requirements.txt`
- `cd /home/rocco/hypertrophyapp && apps/api/.venv/bin/python importers/reference_corpus_ingest.py --reference-dir reference --guides-dir docs/guides`

Outputs:
- `docs/guides/asset_catalog.json`
- `docs/guides/provenance_index.json`
- `docs/guides/generated/*.md`

Notes:
- This pipeline is never part of runtime request handling.
- PDF extraction requires `pypdf`.
- XLSX template imports now preserve `source_workbook` provenance and emit explicit `import_diagnostics` warnings instead of silently dropping ambiguous rows.

## Documentation Map

Execution and priority:
- `docs/Master_Plan.md`
- `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
- `docs/GPT5_MINI_HANDOFF.md`

Architecture and contracts:
- `docs/Architecture.md`
- `docs/Canonical_Program_Schema.md`
- `docs/High_Risk_Contracts.md`
- `docs/Offline_Sync_Deterministic_Contract.md`
- `docs/Security_Hardening_Architecture.md`
- `docs/Auth_Expansion_Architecture.md`

Onboarding redesign/parity:
- `docs/redesign/Onboarding_Reference_Analysis_Batch1.md`
- `docs/redesign/Onboarding_Reference_Analysis_Batch2.md`
- `docs/redesign/Onboarding_Reference_Analysis_Batch3.md`
- `docs/redesign/Onboarding_Reference_Process_Map.md`

## Monorepo Layout

- `apps/web` -> Next.js client
- `apps/api` -> FastAPI service
- `packages/core-engine` -> deterministic planning logic
- `programs` -> canonical versioned program templates
- `importers` -> build-time import scripts
- `reference` -> raw source corpus (non-runtime)
- `infra` -> compose/caddy/scripts
- `docs` -> architecture, contracts, plans, validation

## CI

Mini-validate (runs on PRs):

![mini-validate](https://github.com/Shadowgar/hypertrophyapp/actions/workflows/mini-validate.yml/badge.svg)

