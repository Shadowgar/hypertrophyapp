# GPT-5-mini Execution Backlog (Safe Takeover)

## Goal
Ship remaining project scope end-to-end, including backend, frontend, tests, docs, and validation.

## Execution Rule for GPT-5-mini
- GPT-5-mini owns implementation, validation, commit, and push to `main`.
- Complete one task at a time, then continue to the next highest-priority incomplete task.

## Inputs
- API contracts in `docs/GPT5_MINI_HANDOFF.md`
- Product direction in `docs/Master_Plan.md`

## Sprint A — Program Selection UX (UI-only)

### Task A1 — API client support
- File: `apps/web/lib/api.ts`
- Add:
  - `ProgramTemplateSummary` type
  - `api.listPrograms()` -> `GET /plan/programs`
  - optional `template_id` param support in `api.generateWeek(templateId?)`
- Acceptance:
  - Type-safe compile
  - No change to existing endpoint paths

### Task A2 — Onboarding program picker
- File: `apps/web/app/onboarding/page.tsx`
- Add:
  - fetch `api.listPrograms()` on load
  - selector for `selected_program_id`
  - include `selected_program_id` in `/profile` payload
- Acceptance:
  - Onboarding saves selected program
  - Existing onboarding flow still works if program fetch fails (fallback to `full_body_v1`)
 
 Status: COMPLETED by Codex — `apps/web/app/onboarding/page.tsx` now fetches `/plan/programs` and persists `selected_program_id`.

### Task A3 — Settings program switcher
- File: `apps/web/app/settings/page.tsx`
- Add:
  - show current `profile.selected_program_id`
  - fetch and render program options
  - save changes through existing `/profile` upsert
- Acceptance:
  - User can change selected program without breaking other profile fields

 Status: COMPLETED by Codex — `apps/web/app/settings/page.tsx` includes program selector and saves via `/profile`.

### Task A4 — Week page override
- File: `apps/web/app/week/page.tsx`
- Add optional override selector using `api.listPrograms()` and call `api.generateWeek(selectedOrUndefined)`
- Acceptance:
  - default button uses server-selected program
  - override path works and still returns week plan

Status: COMPLETED by Codex — `apps/web/app/week/page.tsx` now supports an optional program override and passes template id to `POST /plan/generate-week`.

## Sprint B — Plan Guide Scaffolding (UI route structure)

### Task B1 — Program guide index route
- Add route: `apps/web/app/guides/page.tsx`
- Display available programs from `api.listPrograms()`.

Status: COMPLETED by Codex — `apps/web/app/guides/page.tsx` lists available programs and links to program guide pages.

### Task B2 — Program detail guide route
- Add route: `apps/web/app/guides/[programId]/page.tsx`
- Render text-first placeholders sourced from existing summary fields.

Status: COMPLETED by Codex — program detail guide is implemented at `apps/web/app/programs/[id]/page.tsx` (route naming differs from original draft).

### Task B3 — Exercise guide placeholder route
- Add route: `apps/web/app/guides/[programId]/exercise/[exerciseId]/page.tsx`
- Render deterministic placeholders and link back to program guide.

Status: COMPLETED by Codex — exercise guide route implemented at `apps/web/app/guides/[programId]/exercise/[exerciseId]/page.tsx` and renders text-first exercise details when available in program templates.

Acceptance for Sprint B:
- Routes compile
- No runtime PDF rendering/parsing
- No new backend contract requirements

## Guardrails (Must Follow)
- Keep deterministic runtime rules (no runtime PDF/XLSX parsing).
- Keep tests green and maintain API compatibility unless explicitly updated across callers/tests.
- API tests are Postgres-first; use `TEST_DATABASE_URL` only for explicit local overrides.

## Validation per Task

```bash
cd /home/rocco/hypertrophyapp

docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py -q'

cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Escalation
Escalation is optional and only needed when external approvals are required.






## Progress Sync (2026-03-06)
- Repository state synchronized through commit `1026d25` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `63 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
  - `cb317d0`: hardened `scripts/mini_validate.sh` with compose command detection and one-shot rebuild/retry fallback for failed containerized API test runs
  - `3596622`: migrated auth stack from `passlib/python-jose` to `bcrypt/PyJWT` in API runtime paths
  - `1026d25`: added coach-preview API edge-case tests for invalid template handling, low-readiness deload extension, and phase-transition boundary branches
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - `passlib` and `python-jose` deprecation warnings removed from validation output.
  - `mini_validate` run now reports clean test results without warning spam in the default path.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

