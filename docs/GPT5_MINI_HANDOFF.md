# GPT-5-mini Handoff Guide

## Purpose
This document defines exactly what GPT-5-mini should build next, what is already locked, and what must not be changed without GPT-5.3-Codex review.

## PR Ownership Rule
- GPT-5-mini is responsible for task implementation and local validation only.
- Pull request creation, review, merge workflow, and PR troubleshooting are owned by a human or GPT-5.3-Codex.
- If a session drifts into PR process work, redirect immediately to the next backlog implementation task.

Related operating docs:
- `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
- `docs/GPT5_MINI_RUNBOOK.md`
- `docs/GPT5_MINI_BOOTSTRAP_PROMPT.md`
- `docs/Master_Plan.md` (`Model Ownership & Quality Routing`)

Automation scripts:
- `scripts/mini_preflight.sh`
- `scripts/mini_validate.sh`

## Locked Contracts (Do Not Change)

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

## GPT-5-mini Allowed Scope (Next)

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

## GPT-5-mini Forbidden Scope (Without Codex Review)
- Any changes to `packages/core-engine` planning behavior.
- Any schema changes to user/workout tables.
- Any auth/security changes.
- Any migration edits once applied.
- Any changes to the semantics of locked endpoint responses.

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
- No edits to locked-contract files unless explicitly approved.
- PR workflow tasks are deferred to human/Codex owner.
