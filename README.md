# Rocco's HyperTrophy Plan Monorepo

Deterministic hypertrophy planner + workout runner for local-first deployment.

## About

Rocco's HyperTrophy is an explainable, deterministic adaptive hypertrophy coaching platform. It is designed to produce reproducible weekly workout plans and live coaching guidance from canonical program templates and explicitly distilled coaching rules. The project emphasizes local-first development, deterministic decision-making, and structured decision traces so that every automated coaching choice can be inspected and tested.

Core goals:
- Produce deterministic, testable workout plans from authored templates.
- Make adaptation decisions auditable via structured `decision_trace` payloads.
- Keep runtime free of direct PDF/XLSX parsing — ingestion is a build-time step.
- Expose clear boundaries: routers handle auth/SQL/persistence, `packages/core-engine` owns deterministic logic.

## How it works (high level)

1. Authoritative inputs (build-time)
   - Program templates live in `programs/` (JSON canonical templates).
   - Coaching doctrine and rules are distilled from source guides into typed rule artifacts under `docs/rules/` by build-time importers in `importers/`.

2. Runtime inputs
   - User profile, onboarding answers, and persisted workout logs (`WorkoutSetLog`, `ExerciseState`, soreness/check-ins, weekly-reviews`).

3. Core engine
   - `packages/core-engine` consumes templates + rules + canonical `UserTrainingState` to produce deterministic outputs: coach previews, generated-week plans, frequency-adaptation recommendations, live workout guidance, and progression decisions.
   - All meaningful coaching logic and payload normalization live here; engine helpers emit structured `decision_trace` data for auditability.

4. API layer
   - `apps/api` provides HTTP endpoints, authorization, SQL reads/writes, and validation. Routers delegate deterministic decisions and payload shaping to core-engine helpers and keep only persistence/error mapping responsibilities.

5. Web UI
   - `apps/web` is a Next.js client that calls the API to display generated plans, run workouts, log sets, present coach previews, and surface adaptation suggestions.

6. Live loop (runtime)
   - User runs a session in the web UI -> logs sets -> API persists logs and state -> core-engine evaluates performance, fatigue, and substitution/deload signals -> engine may produce adaptation recommendations for future weeks or immediate substitutions -> updated state influences the next generated-week or coach-preview.

Primary flows (simple):
- Onboarding: collects preferences and bootstraps the first plan.
- Generate-week: engine creates a weekly plan from template + user-state.
- Workout run & log: user follows sessions, logs sets; API persists logs and updates `ExerciseState`.
- Post-session evaluation: engine computes progression/fatigue and may emit substitutions or adaptation suggestions.
- Frequency adaptation: preview/apply flow to adjust weekly slot frequency deterministically.

Developer notes
- Run import/ingestion scripts only when updating the `reference/` corpus; runtime must not rely on parsing PDFs/XLSX.
- Use direct venv executables in `apps/api` (e.g., `.venv/bin/python`) instead of `source`-ing activation scripts.
- Keep business logic in `packages/core-engine` and leave routers limited to SQL and HTTP concerns.

## Key Endpoints (API)

- **Auth**
   - `POST /auth/register` — create account
   - `POST /auth/login` — obtain auth token
   - `POST /auth/password-reset/request` and `POST /auth/password-reset/confirm`
   - `POST /auth/dev/wipe-user` — developer-only wipe (environment gated)

- **Profile & Onboarding**
   - `GET /profile`, `POST /profile` — profile upsert and read
   - `GET /profile/training-state` — canonical `UserTrainingState` payload
   - `GET /profile/program-recommendation`, `POST /profile/program-switch`
   - `POST /weekly-checkin`, `POST /weekly-review`
   - `POST /profile/dev/wipe` — clear current test user data (dev only)

- **Plan / Coaching**
   - `POST /plan/generate-week` — generate a deterministic week plan
   - `POST /plan/intelligence/coach-preview` — preview coaching recommendations
   - `POST /plan/adaptation/preview` and `POST /plan/adaptation/apply` — frequency adaptation flows
   - `GET /plan/intelligence/recommendations` — timeline of persisted recommendations
   - `GET /plan/guides/programs/{program_id}` — program guide summary

- **Workout**
   - `GET /workout/today` — today's session or resume candidate
   - `POST /workout/{workout_id}/log-set` — log a set (may return `starting_load_decision_trace` or `substitution_recommendation`)
   - `GET /workout/{workout_id}/progress`, `GET /workout/{workout_id}/summary`

- **History**
   - `GET /history/calendar` and `GET /history/day/{day}`

Notes: many engine responses include a `decision_trace` field for auditability; check plan/workout preview and adaptation responses for `decision_trace` and `request_runtime_trace` fields.

## Developer Quickstart (local dev)

1. Set up API venv and install deps:

    `cd apps/api && python3 -m venv .venv && .venv/bin/python -m ensurepip --upgrade && .venv/bin/pip install -r requirements.txt`

    (install local engine package for editable testing)
    `cd apps/api && .venv/bin/python -m pip install -e ../../packages/core-engine`

2. Run API locally:

    `cd apps/api && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

3. Run web dev:

    `cd apps/web && npm install && npm run dev`

4. Run full validation (API + web tests + build): from repo root, `./scripts/mini_validate.sh`.

5. Verify the Phase 1 path (dogfood): follow `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md` — reset to clean Phase 1 (Onboarding → Developer Tools → "Reset Current User to Clean Phase 1" or `POST /profile/dev/reset-phase1`), then generate week → Today → log set → check-in → review → history → adaptation → regenerate week.

6. Run focused API tests (SQLite override):

    `cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local.db .venv/bin/python -m pytest tests/test_workout_*.py -q`

7. Clean temp DB files after runs:

    `rm -f apps/api/test_local*.sqlite3`

Common gotchas:
- If `apps/api/.venv` is missing pip, run apt and ensurepip then install deps (see `docs/debugging.md` notes in repo memory).
- If `./scripts/mini_validate.sh` fails due to Docker image snapshot issues, rebuild the API image: `docker compose build --no-cache api`.


## Current Status

- The Phase 1 gold path (`pure_bodybuilding_phase_1_full_body`) is fully implemented end-to-end (onboarding → generate week → today → log set → weekly check-in/review → history → frequency adaptation).
- Runtime architecture is deterministic and template-driven; all meaningful coaching decisions live in `packages/core-engine` decision-family modules and emit `decision_trace` payloads.
- Onboarding has a multi-step funnel with profile persistence, developer-safe reset controls, and first-plan bootstrap.
- Frequency adaptation preview/apply is wired across API + web settings for the Phase 1 program.
- Calendar training history view is delivered with clickable day drill-down and same-weekday progression comparison on `/history`.
- Phase C build tools for the administered program are in place:
  - Schema validation tests for program templates, onboarding packages, and coaching rules (`apps/api/tests/test_schema_validation.py`).
  - Canonical XLSX → template + onboarding importer v2 (`importers/xlsx_to_canonical_v2.py`).
  - PDF-to-rules distillation v2 for typed coaching rules with provenance (`importers/pdf_doctrine_rules_v2.py`).

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
- `docs/contracts/High_Risk_Contracts.md`
- `docs/contracts/Canonical_Program_Schema.md`

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
- `docs/flows/Onboarding_and_Flows.md`
- `docs/redesign/Onboarding_Reference_Process_Map.md`
- `docs/architecture/Auth_Expansion_Architecture.md`

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

Read first:
- `docs/DOCUMENTATION_STATUS.md`
- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
- `docs/current_state_decision_runtime_map.md`
- `docs/Architecture.md`
- `docs/Master_Plan.md`

Supporting contracts:
- `docs/Architecture.md`
- `docs/contracts/Canonical_Program_Schema.md`
- `docs/contracts/High_Risk_Contracts.md`
- `docs/contracts/Offline_Sync_Deterministic_Contract.md`
- `docs/architecture/Security_Hardening_Architecture.md`
- `docs/architecture/Auth_Expansion_Architecture.md`

Onboarding redesign/parity:
- `docs/redesign/Onboarding_Reference_Analysis_Batch1.md`
- `docs/redesign/Onboarding_Reference_Analysis_Batch2.md`
- `docs/redesign/Onboarding_Reference_Analysis_Batch3.md`
- `docs/redesign/Onboarding_Reference_Process_Map.md`

Archived AI handoff/runbook material now lives under `docs/archive/ai-handoffs/`. Treat it as historical context, not architectural authority.

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
