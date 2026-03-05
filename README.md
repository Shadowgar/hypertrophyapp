# Rocco's HyperTrophy Plan Monorepo

Deterministic hypertrophy planner + workout runner for Raspberry Pi-hosted local-first deployment.

## Stack

- Web: Next.js (App Router) + React + TypeScript + Tailwind + shadcn-style components
- API: FastAPI + PostgreSQL
- Engine: Python `core-engine` package (deterministic progression/scheduling)
- Infra: Docker Compose + Caddy reverse proxy

## Quick Start (Raspberry Pi Ubuntu 24.04 aarch64)

1. Install Docker + Compose plugin.
2. Copy env file:
   - `cp .env.example .env`
3. Start services:
   - `docker compose up --build`
4. Open app on your LAN Pi IP:
   - `http://<pi-ip>:18080/`
5. API health check:
   - `http://<pi-ip>:18080/api/health`

## Database Migrations (Alembic)

- Create/upgrade schema inside API container:
   - `docker compose exec api alembic upgrade head`
- Create a new migration revision:
   - `docker compose exec api alembic revision -m "your_change"`

## API Tests (Postgres-First)

- API tests default to PostgreSQL for runtime parity.
- By default tests use:
   - `TEST_DATABASE_HOST` or `DATABASE_HOST` or `POSTGRES_HOST` (default `localhost`)
   - `TEST_DATABASE_PORT` or `DATABASE_PORT` (default `5432`)
   - `TEST_DATABASE_NAME` or `POSTGRES_DB` (default `hypertrophy_test`)
   - `TEST_DATABASE_USER` or `POSTGRES_USER` (default `hypertrophy`)
   - `TEST_DATABASE_PASSWORD` or `POSTGRES_PASSWORD` (default `hypertrophy`)
- Full override for one-off local runs:
   - `TEST_DATABASE_URL=sqlite:///./test_local.db`

Examples:

- Postgres-backed test run:
   - `cd apps/api && .venv/bin/pytest tests -q`
- Temporary SQLite override:
   - `cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local.db .venv/bin/pytest tests/test_health.py -q`

## Monorepo Layout

- `apps/web` — Next.js mobile-first PWA client
- `apps/api` — FastAPI service
- `packages/core-engine` — deterministic planning/progression logic
- `programs` — canonical versioned program templates
- `importers` — build-time import scripts (xlsx -> program JSON)
- `reference` — raw documents for human/offline build context only
- `infra` — compose/caddy/scripts
- `docs` — project control docs and architecture

## Runtime Determinism Rules

- Runtime never parses PDFs/XLSX and never uses vector/search retrieval.
- All guide knowledge is encoded into versioned templates and deterministic code rules.
- Program generation uses only persisted user/profile/history + canonical templates.

## Build-Time Reference Corpus Ingestion

Generate deterministic reference artifacts (asset catalog, provenance index, normalized guide docs):

- `python3 importers/reference_corpus_ingest.py --reference-dir reference --guides-dir docs/guides`

Outputs:

- `docs/guides/asset_catalog.json`
- `docs/guides/provenance_index.json`
- `docs/guides/generated/*.md`

Notes:

- This pipeline is build-time only and must never run in runtime request paths.
- PDF extraction uses `pypdf` when available; EPUB/XLSX extraction is deterministic via zip/XML parsing.

## CI

Mini-validate (runs on PRs):

![mini-validate](https://github.com/Shadowgar/hypertrophyapp/actions/workflows/mini-validate.yml/badge.svg)

