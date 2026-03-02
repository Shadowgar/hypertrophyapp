# HypertrophyApp Monorepo

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
