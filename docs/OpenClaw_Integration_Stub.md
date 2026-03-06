# OpenClaw Integration Stub (Post-MVP)

OpenClaw integration is intentionally excluded from MVP to preserve deterministic delivery and reduce drift.

## Deferred Scope
- No OpenClaw runtime calls in MVP.
- No planning or progression decisions delegated to external agentic tooling.

## Future Integration Guardrails
- Any future integration must keep deterministic planning as default path.
- External tools may assist authoring/build-time workflows only unless explicitly approved in Master Plan.
- Runtime fallback must always exist without OpenClaw.


## Progress Sync (2026-03-06)
- Repository state synchronized through commit `739cb99` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - Remaining warnings are dependency-level (`passlib` `crypt` deprecation and upstream `utcnow` deprecations in SQLAlchemy/JOSE call paths).
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

