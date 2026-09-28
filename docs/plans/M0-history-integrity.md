# M0-HIST: occurrence, retry, undo and correction integrity

Date: 2026-09-28. Status: **Proposed bounded application-development package, prepared for owner review**. Preparation/next priority explicitly authorized after SEC-S1 activation; runtime implementation, schema migration and deployment are not authorized by this document or performed in the preparation task. Baseline: merged main `250a0912adccb509024bc3f06a057831d4eb382b`. [Plan registry](README.md); [M0 roadmap](../roadmap/milestones.md); [S1 cutover](../evidence/2026-09-28-sec-s1-cutover.md).

## Problem, outcome and authority

The [completed audit](../audits/2026-09-28-codebase-product-documentation-audit.md) established reused workout strings across weeks, duplicate retry insertion, unqualified state races and undo rebuilding session counts while leaving ExerciseState stale. S1 changed none of these paths. The next package must preserve distinct occurrences, commit one logical operation on retry, retain concurrent records, and make undo/correction remove every derived effect of ineffective work.

Controlling context: [product contract](../requirements/product-contract.md), [constitution](../governance/constitution.md), [ADR-005](../adr/0005-training-history-identity-and-correction.md), [ADR-009](../adr/0009-production-schema-and-data-authority.md), [execution contract](../contracts/execution-plan.md), [data model](../architecture/data-model.md), [runtime authority](../architecture/runtime-authority.md), [catalog](../requirements/catalog.md) and [traceability](../requirements/traceability.md). ADR mechanisms remain Proposed. Desired integrity outcomes do not choose a migration or concurrency strategy by themselves.

Requirements: HIST-001–HIST-005, DATA-004, DATA-005, UX-004 and PERF-010. DATA-004 covers explicit/unknown unit and load-basis identity here, not activation of a new M2A load algorithm. DATA-005 covers prescription/source provenance needed for reconstruction, not a full program-compiler rewrite. Authored Phase 1, Authored Phase 2 and Customized remain separate; source prescriptions and metadata scoring are unchanged.

## Affected owners and bounded interfaces

| Owner / surface | Package responsibility |
|---|---|
| [Persisted models](../../apps/api/app/models.py), `apps/api/alembic/versions/` | Additive user-owned occurrence, command and effective-record identity; retain ambiguous legacy rows honestly. Exact storage/constraints require review. |
| [Workout router](../../apps/api/app/routers/workout.py): `workout_today`, `log_set`, `undo_last_set`, `workout_progress`, `workout_summary` | Bind reads/writes to occurrence/revision; retry/correction transaction boundary; no read-side reinterpretation of completed work. |
| [History router](../../apps/api/app/routers/history.py): calendar/day/exercise/analytics | Query effective records and actual occurrence context; distinguish partial activity from completed work. |
| Deterministic derived-state owners and API persistence | Reconstruct session counts, ExerciseState and dependent guidance from effective records under named existing/versioned rules; no independent shadow formula. |
| [Web runner](../../apps/web/app/today/page.tsx), history views and retry/cache callers | Preserve command identity across retries; account/occurrence-scoped resume and invalidation; present conflicts and corrections. |
| Existing tests | Extend [session-state](../../apps/api/tests/test_workout_session_state.py), [history calendar](../../apps/api/tests/test_history_calendar.py), [analytics](../../apps/api/tests/test_history_analytics.py), [runner](../../apps/web/tests/today.runner.test.tsx) and [log-set](../../apps/web/tests/today.logset.test.tsx) behavior coverage. Their existence is not proof that the new criteria already pass. |

Before editing behavior, follow the scoped context manifest's common_governance and database_migrations groups plus every affected authored_behavior, scheduling_routing, progression_load, customized_generation or source_ingestion group. Resolve a newly discovered consumer as a bounded compatibility question; do not repeat a repository-wide audit.

## Proposed implementation sequence

1. **Fix the command/data contract first.** Review the minimum additive relational mechanism, started-prescription snapshot, ownership/uniqueness rules, request digest and conflict/error contract. Specify deterministic correction/projection reconstruction and a synthetic legacy mapping report. Obtain explicit package/mechanism authorization before migrations or runtime edits; no global event-sourcing mandate.
2. **Introduce occurrence binding end to end.** Distinct weeks and repeated source slots receive distinct workout/exercise occurrence identities with user, plan revision and original source slot lineage. Bind started work to its immutable prescription. Preserve confirmed performed variants separately. Existing unambiguous records may be linked under reviewed rules; ambiguous rows remain accessible and explicitly unresolved.
3. **Make set commands transactional and retry-safe.** Scope the client command ID to user/occurrence and normalize its payload under a reviewed contract. Identical retries return the original record/result; changed payload conflicts without mutation. Qualify database uniqueness and lock/optimistic-revision handling for simultaneous retries and distinct commands. Record plus projection writes are atomic or use an explicitly reviewed recoverable protocol. A failed commit must not acknowledge success.
4. **Make undo/correction reconstruct effective state.** Keep an auditable before/after or amendment/void trail, expected revision and command identity. Repeated undo must not remove another set. Rebuild affected session and exercise projections and invalidate dependent recommendations/evidence. Preserve original prescription, actual observations and nullable effort. [Load](../contracts/load-progression.md) and [recommendation](../contracts/recommendations.md) contracts define the future evidence boundary; this package does not silently activate new progression thresholds or redefine completed-exposure coaching.
5. **Wire runner/history/cache reconciliation.** Key drafts/resume by authenticated user and occurrence; clear private caches on account transition. Reuse command IDs after interrupted responses. Reconcile from effective server records after retries/corrections. Show partial/closed/completed states truthfully and preserve immutable completed prescription/history when plans are regenerated. First qualification uses synthetic data and disposable databases; live backfill/deployment needs its own approved cutover.

Each slice includes its negative tests and trace facts. Do not postpone integrity tests until the final UI slice or mix unrelated baseline-test fixes into this package.

## Required acceptance matrix — proposed, not executed

| Case | Required result / evidence |
|---|---|
| Same template workout in two weeks | Progress, records and caches remain isolated even if legacy workout strings match. |
| Same catalog exercise twice in one workout | Distinct source/exercise occurrences and set records; no collapsed slots. |
| Identical command retried after response loss | Same persisted logical set and result; no second row or progression effect. |
| Same command ID with different normalized payload | Explicit conflict; original record/projection preserved. |
| Simultaneous identical retries / distinct valid writes | One result for identical retries; both distinct records survive and projections match effective records. Isolated PostgreSQL required. |
| Undo/correction, including replayed undo | Audit trail retained; ineffective work stops affecting session counts, ExerciseState, completion and dependent advice; replayed undo cannot delete the next set. |
| Stale revision / ownership mismatch | Conflict or forbidden/not-found according to the approved contract, with no cross-user mutation or overwrite. |
| Mid-transaction failure | No acknowledged partial record/projection state; deterministic retry/rebuild after recovery. |
| Planned versus performed load, missing effort, technique children | Preserve actual values and unknown units/effort; warm-up/child/void/duplicate records do not create extra ordinary effective sets/exposures. No authored prescription mutation. |
| Partial activity and completed prescription | Calendar distinguishes logged activity from full completion; undo/correction revises derived completion without rewriting the original prescription. |
| Regeneration/reschedule after started/completed work | Existing occurrence and prescription/history remain reconstructible; no automatic replacement of started work. |
| Legacy ambiguity / interrupted runner / account switch | Raw legacy records retained without guessed week/slot/RPE/units; resume is user/occurrence scoped and exposes unresolved mapping. |

Automated evidence must include relevant API/core/web cases, independent reconstruction comparisons, migration upgrade/backfill and failure rehearsal on synthetic legacy data, and controlled PostgreSQL interleavings. SQLite success alone does not qualify races or migration safety. Manual evidence must exercise interrupted response, retry, undo/correction, two-week history and account-transition cache behavior in a real browser. Proposed cases here are not passing tests or product acceptance.

## Decisions and safety gates before execution

Review correction storage (audited edit versus amendments), uniqueness/canonical payload rules, locking/revision protocol, the projection rebuild owner/rule version, ambiguous legacy mapping policy, completion/partial closure semantics and unknown legacy load basis. Choose the smallest mechanism satisfying the approved invariants; do not fabricate facts to make backfill total. UI cache key/clear behavior must follow actual authentication and occurrence ownership, not reusable workout strings alone.

Follow [DB_SAFETY_LOCK.md](../../DB_SAFETY_LOCK.md). Verify explicit disposable DB/log targets and cleared environments before app imports, startup, tests or migration rehearsals. Never run reset helpers, drop/create reset pairs, destructive SQL or Compose volume deletion against live data. Do not copy live user data into test fixtures. Before any live schema/backfill cutover, separately approve operator scope, compatible backup/restore evidence, additive rollout and rollback/forward-recovery procedure. Nothing in this package authorizes those live operations.

Release qualification names source revision, synthetic dataset, DB version, procedures/results, failure dispositions and limitations. Keep the known S1 baseline/fixture failures visible; do not weaken assertions merely to obtain a green total. M0-HIST acceptance, detailed ADR acceptance and whole-M0/release acceptance remain separate explicit decisions.

## Exclusions and handoff

No S1 quick-start cleanup loop, S2 auth-version/session/abuse implementation, source importer repair, Authored/Customized policy change, new progression rule, date allocator, metadata scoring activation, whole offline framework or production migration is bundled here. The deferred PR #38 P2 remains recorded in [S1 evidence](../evidence/2026-09-28-sec-s1-cutover.md).

Next implementation task should name this package, select/authorize the bounded first slice and its mechanism, and provide an isolated verification target. Preparation is complete; application development has not started. SEC-S2 remains independently pending and must not be presented as completed by the signing-key cutover.
