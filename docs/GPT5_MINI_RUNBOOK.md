# GPT-5-mini Runbook

## Preflight
1. Read:
   - `docs/GPT5_MINI_HANDOFF.md`
   - `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
   - `docs/GPT5_MINI_SUCCESS_PLAN.md`
   - `docs/Master_Plan.md`
2. Confirm current repository state is clean and reproducible.
3. Run automated preflight:

```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_preflight.sh
```

## Working Agreement
- Keep implementation focused: complete one backlog task at a time, end-to-end.
- GPT-5-mini is authorized for full-stack implementation in this repository.
- GPT-5-mini can modify backend, frontend, tests, scripts, and docs as needed.
- Push directly to `main` after validations pass.

## Mini Execution Loop (Required)
1. Choose next task with `./scripts/mini_next_task.sh` (backlog first, then `Master_Plan` fallback).
2. Implement that task across all required files.
3. Run `./scripts/mini_validate.sh`.
4. If validation fails, fix issues and re-run until green.
5. Update docs/checklist notes and continue with next priority task.

## Quick Commands

### One-command session flow
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_session.sh
```

### Session start (pick next backlog task)
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_next_task.sh
```

Use the printed task as the starting target for the current mini session.

### One-command validation
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_validate.sh
```

### API regression checks
```bash
cd /home/rocco/hypertrophyapp
docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests -q'
```

Notes:
- Test suite is Postgres-first for runtime parity.
- Override only for local troubleshooting:
```bash
cd /home/rocco/hypertrophyapp/apps/api
TEST_DATABASE_URL=sqlite:///./test_local.db .venv/bin/pytest tests/test_health.py -q
```

### Web compile check
```bash
cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Failure Handling

### If API test fails
- Re-run only failing test first.
- Fix root cause and re-run full validation.

### If web build fails
- Fix TS/ESLint/local UI logic errors.
- Do not change backend to bypass compile issues.

## Definition of Safe Completion
- Target task acceptance criteria met.
- API regression command passes.
- Web build passes.
- Web test suite passes.
- Working tree is clean after commit.

## Completion Checklist

- Run `./scripts/mini_preflight.sh`.
- Run `./scripts/mini_validate.sh`.
- Add or update tests for changed behavior.
- Commit with clear message and push to `main`.






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

