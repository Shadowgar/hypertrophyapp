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
- Repository state synchronized through commit `cb317d0` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
  - `cb317d0`: hardened `scripts/mini_validate.sh` with compose command detection and one-shot rebuild/retry fallback for failed containerized API test runs
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - Remaining warnings are dependency-level (`passlib` `crypt` deprecation and `python-jose` internal `utcnow` deprecation).
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

