# GPT-5-mini Handoff Guide

## Purpose
This document defines how GPT-5-mini should continue full-stack delivery for the repository.

## Operating Authority
- GPT-5-mini is authorized to implement across the entire project.
- GPT-5-mini may modify backend, frontend, tests, docs, scripts, CI workflows, and migrations when required.
- GPT-5-mini may commit and push directly to `main` after validation passes.

Related operating docs:
- `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
- `docs/GPT5_MINI_RUNBOOK.md`
- `docs/GPT5_MINI_BOOTSTRAP_PROMPT.md`
- `docs/Master_Plan.md` (`Model Ownership & Quality Routing`)
- `docs/High_Risk_Contracts.md`

Automation scripts:
- `scripts/mini_preflight.sh`
- `scripts/mini_validate.sh`

## Core Contracts (Maintain Unless Task Requires Change)

### API Endpoints
- `GET /plan/programs`
  - Returns validated program summaries from `/programs/*.json`.
  - Response shape:
    - `id: string`
    - `version: string`
    - `split: string`
    - `days_supported: number[]`
    - `session_count: number`
    - `description: string`
- `POST /plan/generate-week`
  - Uses `payload.template_id` if provided.
  - Otherwise uses user `selected_program_id`.
  - Otherwise falls back to `full_body_v1`.
  - Request shape (current):
    - `template_id?: string`
- `GET /profile`
  - Must include `selected_program_id`.
- `POST /profile`
  - Must accept and persist `selected_program_id`.

### Data Model
- `users.selected_program_id` exists and is persisted.
- Alembic revision `0006_user_selected_program` introduces this field.

### Determinism Rules
- No runtime PDF/XLSX parsing.
- No runtime embeddings/retrieval.
- All runtime planning from canonical templates in `/programs/`.

## Files Changed by GPT-5.3-Codex
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- `apps/api/app/program_loader.py`
- `apps/api/app/routers/profile.py`
- `apps/api/app/routers/plan.py`
- `apps/api/alembic/versions/0006_user_selected_program.py`
- `apps/api/tests/test_program_catalog_and_selection.py`

## GPT-5-mini Scope (Next)

### 1) Onboarding Program Picker (UI)
- Add selectable program list in `apps/web/app/onboarding/page.tsx`.
- Use `GET /plan/programs`.
- Save chosen `selected_program_id` through `/profile`.

### 2) Settings Program Switcher (UI)
- Add program switch UI in `apps/web/app/settings/page.tsx`.
- Persist via `/profile`.
- Display current program summary.

### 3) Plan Guide Pages (UI Scaffolding)
- Add initial route structure for guide surfaces:
  - program overview
  - day/session overview
  - exercise guide
- Use text-first rendering from API-ready structures (no PDF rendering).

### 4) Week Page Program UX
- Add optional explicit program override on week generation UI.
- Keep default behavior as server-side selected program.

## Notes on Safe Evolution
- Prefer additive and backward-compatible API changes.
- If a breaking change is required, update callers and tests in the same session.
- Keep deterministic runtime rules: no runtime PDF/XLSX parsing or embeddings-based retrieval.

## Deterministic Boundaries (Do / Do-Not-Change)

### DO (allowed)
- Additive API fields that do not break existing consumers.
- New tests for deterministic behaviors and contract enforcement.
- UI composition and visual updates that do not alter deterministic planning behavior.
- Build-time importer improvements that preserve deterministic outputs and schema validity.

### DO NOT CHANGE without explicit contract update
- Engine payload keys/semantics consumed by API/web (`weekly_volume_by_muscle`, `muscle_coverage`, `mesocycle`, `deload`, session/exercise structure).
- Runtime determinism constraints (no runtime parsing of `/reference`, no runtime retrieval/embeddings).
- Program switching semantics (two-step explicit confirmation flow).
- Guide API route contracts and error semantics without coordinated caller/test updates.
- Ingestion artifact contract files (`asset_catalog.json`, `provenance_index.json`) and aggregate signature semantics.

### If a prohibited change is required
1. Update `docs/High_Risk_Contracts.md` first.
2. Update all affected API/web/tests in one PR.
3. Run focused validation for the changed contract surfaces.

## Validation Commands

### API tests (container)
```bash
cd /home/rocco/hypertrophyapp
docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py -q'
```

### Web build
```bash
cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Definition of Done for mini tasks
- UI reads from `/plan/programs` and persists `selected_program_id`.
- No regressions in API tests above.
- Web build passes.
- Web tests pass.
- Changes are committed and pushed to `main`.
