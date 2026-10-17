# M4-C3B1 account-owned candidate lifecycle implementation plan

> **For agentic workers:** use superpowers:executing-plans inline. The owner authorized engineering and a stacked draft through Issue #92; no additional design permission is inferred or required for that scope.

**Goal:** bind the existing nonprescriptive C3A preview to an authenticated account's immutable, versioned candidate and explicit, replay-safe consent.

**Architecture:** retain C1/C2 planning and C3A serialization as the only training decision owners. Add a lifecycle orchestrator with transactional append-only storage and versioned scheduling ports. Only an uninstalled synthetic SQLite adapter supplies persistence. A separate, unregistered factory reuses the existing bearer/current-user dependency through an explicit bridge. There is no workout writer or production migration.

**Tech stack:** existing Python, FastAPI/Pydantic, standard-library SQLite in research only; no dependencies added.

**Spec:** [Issue #92](https://github.com/Shadowgar/hypertrophyapp/issues/92) and [owner review](https://github.com/Shadowgar/hypertrophyapp/pull/90) (read via GitHub; review date 2026-10-16). This plan records implementation choices, not accepted ADRs or scientific policies.

## Global constraints

- Activation remains disabled even after future cryptographic admission. No real policy/key/inventory is bundled.
- No production registration, schema, histories, Authored source or #83 date-routing changes.
- Numerical rules remain provisional. Short candidate acknowledgement is distinct from scientific approval.
- Explicit isolated environment and disposable targets before imports/tests. No reset/drop/delete SQL.
- New revisions never overwrite earlier snapshots, receipts, date selections or source occurrences.

## Review focus

- Cross-account/session challenge reuse must fail without revealing another user's proposal.
- Retry after withdrawal must return the historical receipt without resurrecting consent.
- Policy/catalog/history/scheduling changes must invalidate pending consent, including correction/undo.
- Missing restriction/skill/effort must remain unknown; no time-cap truncation or invented clearance.
- Arbitrary client evidence/signers/omission tokens cannot supply activation authority.

## Task 1: immutable preview evidence and transactional lifecycle

Files: extend `apps/api/app/customized_preview_service.py`; create `customized_lifecycle_models.py`, `customized_lifecycle.py`, `customized_lifecycle_schedule.py`; test-only `research/m4c3b1/store.py`; tests `apps/api/tests/test_customized_lifecycle.py`.

Interfaces: `evaluate_preview` returns response plus typed internal evidence; `LifecycleService` creates/reads/revises/challenges/accepts/declines/withdraws/checks activation through account-bound commands. `SchedulePort.resolve(subject, timezone)` returns the exact planning context, revision and adjacent occurrence evidence. `ProposalStore.transaction()` atomically appends owned events and idempotency receipts.

- [x] Write failing tests for immutable short/long candidate snapshots, exact challenge acknowledgements, revisions, retry/conflict, account/session isolation, stale evidence and protected Authored dates.
- [x] Run targeted tests RED; implement ports, state transitions and append-only disposable adapter; run GREEN.
- [x] Commit task with recorded test evidence.

## Task 2: guarded authenticated nonproduction flow

Files: `customized_lifecycle_http.py`, `customized_lifecycle_view.py`, test-only demo/fixtures and focused HTTP tests.

Interfaces: separate factory takes trusted account dependency, lifecycle service and exact trusted origin. Existing app authentication can be mapped explicitly; disabled/default/production access fails before auth or persistence. JSON commands and HTML review share the same actual stored preview. UI uses bearer authorization, bounded same-origin requests and explicit consent. No cookie fallback or activation endpoint.

- [x] Write failing HTTP tests for real JWT/current-user bridge using disposable account lookup, missing/wrong bearer, scope/origin, safe errors/size, IDOR and revision flow.
- [x] Implement, run GREEN, demonstrate desktop/mobile preview→challenge→accept→blocked→revision/decline and stale conflict.
- [x] Commit task.

## Task 3: scoped qualification and draft

- [x] Run new tests plus applicable C1/C2/C3A and Authored/load/profile regression subsets; no unrelated broad baseline reruns.
- [x] Run docs/diff checks, fresh independent scoped review and Codex Security workflow where available; disclose export limits honestly.
- [x] Record exact manifest, commands/results, demo and C3B2 decisions; publish separate stacked draft on verified C3A head `3fe4ef381fee730ea13e0957201dd9bfe57ae9dc`.

## Execution record

Initial ruling: implement inline, with a fresh final reviewer as required by the execution/review skills. User authorization supersedes repeated plan approval pauses. Disposable append-only SQLite qualifies only this adapter, not production PostgreSQL grants, races or migrations. Schedule reads are rechecked at consent; production transactional scheduling integration remains C3B2.

Task record: implementation commits e7a02cd and 0073732, initial scoped33/account and399 combined passes. Fresh reviewer found three Important boundaries and one related Minor; reproduced and fixed in one pass with seven added API cases and four delayed-response browser cases. Final combined406 passed57.08s, API-cwd subprocess isolation check passed. Source correction/final evidence commits and published head/tree are recorded by the draft PR. Managed security export remains blocked by host permissions; no sealed pass.

Follow-up review: no Critical/Important findings remain; seven added API cases independently rerun. Remaining dirty-input Minor corrected within the same isolated UX scope and final browser regression passed. No deferred review findings.
