# Offline Sync Deterministic Contract (Phase 10)

Purpose: define deterministic, conflict-safe offline logging and replay semantics for workout data so mobile execution remains reliable without introducing runtime nondeterminism.

## Scope

- Web client offline behavior for workout logging actions.
- API replay and idempotency contract for queued mutations.
- Conflict resolution rules for multi-device and stale-state scenarios.
- Sync status surface semantics (UI state labels + transitions).

This document is architecture/contract scope. It does not require immediate full implementation of all queue UX surfaces.

## Non-Negotiable Invariants

- No data mutation is applied twice when the same client operation is replayed.
- Replay ordering is deterministic for a given queue.
- Conflict resolution outcomes are deterministic and inspectable.
- Offline behavior must not bypass existing program/exercise validation constraints.
- Runtime determinism rules remain unchanged (no runtime parsing/retrieval pipelines).

## Client Queue Contract

Queue item shape (logical contract):

- `op_id: string` (UUIDv7 recommended): globally unique operation id.
- `client_id: string`: stable per-installation identifier.
- `entity_type: "workout_log" | "set_log" | "session_event"`.
- `entity_id: string`: deterministic target id.
- `op_type: "create" | "update" | "delete"`.
- `payload: object`: mutation payload.
- `created_at_ms: number`: client timestamp for ordering only.
- `base_version?: number`: optimistic version observed when item was queued.

Deterministic local ordering key:

1. `created_at_ms` ascending
2. `op_id` lexical ascending (tie-breaker)

Queue behavior:

- FIFO replay by deterministic ordering key.
- Failed items remain in queue with terminal error metadata.
- Client must not reorder queued items after enqueue.

## Replay API Contract

Replay calls must include idempotency metadata:

- `X-Client-Id`
- `X-Op-Id`
- Optional body `base_version`

Server behavior:

- If `(client_id, op_id)` has already been applied, return prior success response (idempotent replay).
- If validation fails (schema/business rule), return deterministic `422` and mark queue item terminal.
- If version conflict is detected, return deterministic `409` with server authoritative state/version.
- If transient failure (network/server unavailable), client retries with same `op_id`.

## Conflict Resolution Rules

Conflict classes and deterministic policy:

1. **Duplicate operation replay**
   - Condition: seen `(client_id, op_id)`.
   - Policy: return prior successful result, no additional mutation.

2. **Stale version update**
   - Condition: `base_version` older than server current.
   - Policy: reject with `409`, include server state + current version.
   - Client action: keep item errored; require explicit user retry/accept merge path.

3. **Deleted target update**
   - Condition: target entity no longer exists.
   - Policy: deterministic `409` (not silent recreate).

4. **Cross-device last-write contention on same field**
   - Policy: server-authoritative versioning; no hidden merge heuristics.

### Explicitly forbidden conflict behavior

- No hidden field-level merge.
- No timestamp-only “latest wins” without version checks.
- No silent dropping of conflicting operations.

## Sync Status UX Contract

Allowed user-facing states:

- `synced`: queue empty; no pending failures.
- `pending`: queue has items and replay is in progress.
- `offline`: network unavailable; queue paused.
- `attention`: terminal conflict/validation error requires user action.

Deterministic state transitions:

- `synced -> pending` when first item enqueued and network available.
- `pending -> offline` when connectivity lost.
- `offline -> pending` on connectivity restored and replay resumed.
- `pending -> attention` when terminal `409/422` remains unresolved.
- `pending -> synced` when queue drains with no terminal errors.
- `attention -> pending` only after user-triggered resolve/retry action.

## Persistence & Recovery Contract

- Queue must persist across app restarts (IndexedDB preferred).
- On startup, replay resumes using the same deterministic ordering key.
- Applied operation cache (for idempotency local bookkeeping) must survive restarts long enough to prevent immediate duplicate submissions.

## Observability Contract

For each replay attempt, log structured fields:

- `client_id`, `op_id`, `entity_type`, `entity_id`, `op_type`
- `attempt_number`
- `result`: `applied | duplicate | conflict | validation_error | transient_error`
- `server_version` when available

Metrics minimum:

- queue depth
- replay success rate
- conflict rate (`409`)
- terminal validation failure rate (`422`)

## Test Matrix (Minimum)

1. Duplicate replay with same `op_id` applies once.
2. Deterministic ordering tie-break (`created_at_ms` equal).
3. Stale `base_version` returns deterministic `409`.
4. Invalid payload returns deterministic `422` and terminal queue mark.
5. Restart recovery resumes replay in same deterministic order.
6. Sync status transitions follow contract state machine.

## Change Control

Any change to these semantics requires coordinated updates to:

- API handlers and replay persistence logic
- Web offline queue client logic
- tests for idempotency/conflict behavior
- `docs/contracts/High_Risk_Contracts.md` and `docs/DOCUMENTATION_STATUS.md`






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
