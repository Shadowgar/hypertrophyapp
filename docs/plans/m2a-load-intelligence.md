# M2A-1 completed-exposure load intelligence implementation plan

> For agentic workers: execute the authorized bounded tasks with the Superpowers
> planning/TDD/verification workflow and independent file ownership.

**Goal:** Prefill auditable authored load-only guidance from completed effective
exercise exposures, with optional actual RPE, override and reconstruction.
**Architecture:** Pure core exposure/decision owner, owner-locked API projections,
faithful Today presentation. Generated state and source prescriptions remain
separate. **Tech stack:** Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL;
Next/React/TypeScript; pytest/Vitest/Playwright.
**Spec:** [Bounded design](m2a-load-intelligence-design.md), explicit owner task
2026-10-06, [load contract](../contracts/load-progression.md),
[execution](../contracts/execution-plan.md) and
[recommendations](../contracts/recommendations.md).

## Task 1: pure completed-exposure decisions

- [x] Add failing behavior tests in `test_load_intelligence.py` before code.
- [x] Implement `load_intelligence.py`: summary, comparison key, next-load and
  remaining-set load-only decisions. Core receives plain data and explicit
  source/rules/context; no database, wall clock or LLM.
- [x] Observe red→green for complete/partial/warm-up/child/retry/void boundaries,
  actual versus planned load, nullable RPE, each action, one/two comparable
  failures, repeated-slot/variant/week context, mixed-load abstention and rounding.
- [x] Verify original inputs/source fields remain unchanged and same evidence
  produces identical trace. Preserve existing Generated tests/policies.

## Task 2: API state, effective receipts and additive migration

- [x] Write portable guarded disposable-target regressions before integration.
- [x] Add `AuthoredLoadState` and isolated-only 0022, no historical backfill.
- [x] Implement `workout_load_state.py` with effective owner-bound receipt
  grouping, frozen-source context, unique state and content-bound advice.
- [x] Integrate Authored log/Today/progress/summary/undo/correction and no-write
  load preview. Preserve Generated logging/replay and existing retry hashes.
- [x] Persist recommendation/choice/override/context separately in captured v2
  receipt JSON; expose actual RPE and effective set IDs. Validate finite context
  and RPE 0–10; correction distinguishes omitted effort from explicit null.
- [x] Observe red→green for source invariance, exact completion, retry/void,
  substituted variants, state/advice replay, user ownership and rollback.
- [x] Rebuild affected later advice; no stale qualified load after undo.

## Task 3: practical Today logger and guidance

- [x] Add failing component tests for optional actual RPE, server prefill,
  explicit override, canonical conversion, unknown context and corrections.
- [x] Update `exercise-control.tsx`, Today and web API/identity/guidance helpers.
  Render owned facts, collect explicit load context and retain exact pending
  commands. Keep each authored target and source relationship unchanged.
- [x] Provide receipt correction/undo and authoritative invalidation/refresh.
  Preserve edited next-set drafts; never inherit source guidance into an
  unqualified performed variant. Monitor does not become a zero-load proposal.
- [x] Verify focused tests, types and lint; avoid unrelated visual polish.

## Task 4: isolated PostgreSQL and review

- [x] Verify new disposable database/user/network/mounts before imports/DDL.
- [x] Rehearse 0021→0022 with synthetic legacy rows and immutable hashes/counts.
- [x] Qualify completed-exposure persistence, duplicate retry, simultaneous
  final sets, correction during/after completion, reconstruction and uniqueness.
- [x] Review core/API/UI correctness independently; retain relevant findings
  and require meaningful regressions before qualification.
- [ ] Attempt immutable-range Codex Security qualification; retain actual
  managed-storage status and coverage limits, without a fabricated sealed report.

## Task 5: browser and final stable-head qualification

- [x] Use verified disposable services/users; desktop/mobile RPE logging,
  current remaining-set guidance, completion, next advice/Why, override,
  correction/undo, rest/resume and no overflow/runtime errors.
- [x] Run final relevant broader core/API/web/type/lint/build/docs checks once
  per stable final revision. Compare known baseline names; do not hide reds.
- [x] Record source hashes, real/simulated evidence and remaining M2A limits.

## Task 6: integration and owner handoff

- [x] Record M2B-1 LIVE merge/backup/0021/health/browser evidence and remaining
  M2B scope without claiming whole-track acceptance.
- [ ] Update plan/evidence/traceability registries, commit and push
  `m2a/load-intelligence`; open a PR against main without merge.
- [ ] Inspect exact-head CI, Codex review, all threads and mergeability; fix
  P0/P1 and relevant P2 progression/history/load findings.
- [ ] Confirm no live wipe/reset/reseed/history deletion, only live 0021, no
  live M2A migration, M2A unmerged/unreleased; stop for PR review.

## Review focus

Old retry normalization; warm-up/child finalization; cohort identity excluding
week but preserving repeated source positions; nullable actual effort and
hard source load semantics; correction of earlier evidence; stale UI drafts;
PostgreSQL races and Generated-path isolation.

## Execution record

Owner requested immediate implementation and supplied outcome, boundaries,
tests and review/deployment instructions. Read-only reconnaissance produced the
design above; implementation stays within that authorization. Independent core,
API and web file ownership permits parallel work; root owns integration,
deployment/evidence and final qualification. Unaccepted ADRs remain Proposed.

The integration/review checklist records the pre-publication snapshot. Final
immutable-head CI, Codex review, managed-security retention status and owner
handoff are recorded on the published PR; unchecked publication items do not
authorize merge or live 0022.
