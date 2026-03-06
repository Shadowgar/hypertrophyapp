# GPT-5-mini Full-Project Success Plan

## Objective
Enable GPT-5-mini to complete the entire project autonomously, with consistent quality, deterministic runtime behavior, and continuous delivery to `main`.

## Operating Mode
- GPT-5-mini owns full implementation scope in this repository.
- GPT-5-mini can edit frontend, backend, tests, docs, scripts, CI workflows, and migrations when required.
- Delivery loop is continuous: implement -> validate -> commit -> push -> continue.

## Non-Negotiable Product Rules
- Keep runtime deterministic: no runtime PDF/XLSX parsing and no runtime embeddings retrieval.
- Keep mobile-first dark-mode UX consistent with `docs/Master_Plan.md`.
- Preserve API compatibility unless a task explicitly requires contract evolution; if evolved, update all callers and tests in the same change.

## Execution Algorithm (Use Every Session)
1. Run preflight and validate current baseline:
   - `./scripts/mini_preflight.sh`
   - `./scripts/mini_validate.sh`
2. Select next highest-priority incomplete work item with `./scripts/mini_next_task.sh` (backlog first, then `Master_Plan` fallback).
3. Implement end-to-end (API/UI/tests/docs) for that item only.
4. Run focused tests first (changed areas), then full validation:
   - targeted `pytest` / `vitest`
   - `./scripts/mini_validate.sh`
5. If validation fails, fix root cause and re-run until green.
6. Commit with clear scope message and push to `main`.
7. Update backlog/checklists to reflect completion and move to next item.

## Priority Order to Finish the Program

### P0 — Complete MVP Checkboxes in Master Plan
Prioritize unchecked items in:
- Phase 5 (Workout Runner tests)
- Phase 6 (soreness modifiers determinism, weekly volume, coverage validator)
- Phase 8 (equipment-safe variants, program selection logic, catalog summaries)

Definition of done for P0:
- MVP checklist in `docs/Master_Plan.md` fully satisfied.
- API and web validations pass in CI-equivalent flow.

### P1 — Phase 13 Reference Corpus Intelligence + Guides
Implement deterministic ingestion + guide APIs/pages:
- Build/import asset catalog and deterministic extraction outputs
- Emit `/programs/*.json`, `/docs/guides/*`, provenance index
- Add program/day/exercise guide API endpoints and UI pages
- Add determinism and coverage tests

Definition of done for P1:
- Every `/reference/` asset represented in derived artifacts.
- No runtime ingestion dependencies added.

### P2 — Analytics, Offline, Hardening, Advanced
Deliver phases 9, 10, 11, 12 in order:
- Analytics dashboard + PR logic + charts
- Offline queue/replay/status UX
- Operational hardening (backup/restore/secrets/rate limiting)
- Advanced enhancements (optional RPE, MEV/MAV/MRV, auth expansion)

Definition of done for P2:
- Phase checklists complete with tests.
- Deployment remains Raspberry Pi compatible and Docker Compose stable.

## Quality Gates (Mandatory)
- No push without passing `./scripts/mini_validate.sh`.
- Add/adjust tests for any behavior change.
- Keep commits scoped and reversible (single concern per commit).
- Revert generated artifacts not meant for source control (e.g., build output drift).

## Change Safety Rules
- Prefer additive changes and small migration steps.
- For breaking refactors, include compatibility adjustments in the same commit set.
- Never leave the repository in a red state on `main`.

## Backlog Hygiene Rules
- Track status inline in backlog docs after each shipped task.
- When new work is discovered, append it to the proper phase with acceptance criteria.
- Keep acceptance criteria testable and explicit.

## Session Exit Criteria
- Current task acceptance criteria satisfied.
- Validations green.
- Changes committed and pushed.
- Next task identified and documented.

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

