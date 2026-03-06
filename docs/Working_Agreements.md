# Working Agreements

## No-Drift Rules
1. Deterministic engine first: no runtime retrieval/search/pdf parsing.
2. Scope changes must update `docs/Master_Plan.md` in the same PR.
3. No broad refactors without explicit plan update and acceptance criteria.
4. Template changes must be versioned in `programs/`.
5. API contract changes must be reflected in web client and docs together.

## Commit Discipline
- Keep commits focused and reversible.
- Include docs with behavior changes.
- Do not mix infra rewrites with feature logic unless unavoidable.

## PR Checklist
- [ ] Runtime determinism preserved.
- [ ] Master Plan updated if scope changed.
- [ ] API and UI contracts aligned.
- [ ] Docker Compose boot path still works.
- [ ] New template/schema changes versioned and documented.

## Decision Record Rule
Major design decisions should be appended to architecture docs with rationale and rollback notes.

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

