## PR Draft: mini — Program selection UI, guides, and tests

Summary
- Adds program selection UI to onboarding and settings.
- Adds a program override on the Week page.
- Adds program guide routes and exercise guide placeholders (text-first).
- Adds Vitest UI tests for onboarding, settings, and week flows.
- Updates backend to persist `selected_program_id` (migration `0006_user_selected_program.py`) and exposes program catalog API used by the UI.
- Adds runbook/backlog docs and validation scripts for GPT-5-mini takeover.

Files of interest
- UI: `apps/web/app/onboarding/page.tsx`, `apps/web/app/settings/page.tsx`, `apps/web/app/week/page.tsx`, `apps/web/app/guides/*`, `apps/web/app/programs/*`
- API: `apps/api/app/routers/plan.py`, `apps/api/app/routers/profile.py`, `apps/api/app/program_loader.py`
- Migration: `apps/api/alembic/versions/0006_user_selected_program.py`
- Tests: `apps/web/tests/*`, `apps/api/tests/test_program_catalog_and_selection.py`

Validation performed
- Ran `./scripts/mini_preflight.sh` — passed.
- Ran `./scripts/mini_validate.sh` — full output recorded in `docs/mini_validate_output.txt` and shows:

```
9 passed, 65 warnings
Next.js build succeeded (static pages generated)
[PASS] Mini validation complete.
```

Notes / Guardrails
- This work follows the locked contracts in `docs/GPT5_MINI_HANDOFF.md` — no runtime PDF/XLSX parsing, deterministic planning from `/programs/*.json`.
- Do NOT change `packages/core-engine/**`, `apps/api/alembic/**`, or auth semantics without Codex review.

Suggested reviewers: backend owner, frontend owner, QA.

Next steps (recommended)
1. CI: add a job that runs `./scripts/mini_validate.sh` on PRs to `main`.
2. UI polish and acceptance testing by QA — verify flows end-to-end with a local API.





## Progress Sync (2026-03-06)
- Repository state synchronized through commit `3596622` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
  - `cb317d0`: hardened `scripts/mini_validate.sh` with compose command detection and one-shot rebuild/retry fallback for failed containerized API test runs
  - `3596622`: migrated auth stack from `passlib/python-jose` to `bcrypt/PyJWT` in API runtime paths
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - `passlib` and `python-jose` deprecation warnings removed from validation output.
  - `mini_validate` run now reports clean test results without warning spam in the default path.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

