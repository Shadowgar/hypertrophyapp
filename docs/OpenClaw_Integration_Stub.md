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
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

