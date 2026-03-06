# High-Risk Contracts (Deterministic Core)

Purpose: define the contracts that must remain stable unless a change is intentionally coordinated across engine, API, web, tests, and docs in one session.

## 1) Engine Rules Contract

Scope: `packages/core-engine` and API callers that pass generation inputs.

### Hard invariants
- Runtime generation is deterministic for the same template + inputs.
- Runtime generation must not depend on `/reference` assets.
- Program generation must use canonical templates from `/programs`.
- Output payload must include mesocycle/deload and coverage fields currently consumed by API/web.

### Required payload invariants
- `program_template_id`: selected template used for generation.
- `sessions[]`: deterministic session ordering and per-session `exercises[]`.
- `weekly_volume_by_muscle`: weekly set totals used for validation/UI.
- `muscle_coverage`: includes `minimum_sets_per_muscle`, `under_target_muscles`, and `covered_muscles`.
- `mesocycle`: includes week index + trigger data + deload reason fields.
- `deload`: includes `active`, `set_reduction_pct`, `load_reduction_pct`, `reason`.

### Change policy
- Any change to output keys or semantics requires simultaneous updates to:
  - API serializers and tests
  - web consumers and tests
  - this document + `docs/Master_Plan.md`

## 2) Ingestion Schema Contract

Scope: build-time importers in `/importers` and their generated artifacts.

### Hard invariants
- Ingestion is build-time only; never called by runtime request handlers.
- Supported corpus types are currently `.pdf`, `.epub`, `.xlsx`.
- Outputs are deterministic for the same input files.

### Required outputs
- `docs/guides/asset_catalog.json`
- `docs/guides/provenance_index.json`
- `docs/guides/generated/*.md`

### Required catalog/provenance properties
- Asset-level SHA256 and aggregate signature are stable under unchanged inputs.
- Every supported source asset must appear in both catalog and provenance (no orphans).
- Derived guide document path for each catalog entry must exist.

### XLSX template import invariants
- Imported canonical exercise slots include equipment tags and substitution candidates.
- Spreadsheet YouTube links are mapped to canonical `video.youtube_url` when present.
- Non-YouTube links are not promoted to `video.youtube_url`.

## 3) API Invariants Contract

Scope: endpoints consumed by current web flows.

### Planning and guides
- `GET /plan/programs`: catalog summaries only.
- `POST /plan/generate-week`: deterministic week generation with template selection rules.
- `GET /plan/guides/programs`: guide catalog list.
- `GET /plan/guides/programs/{program_id}`: program guide summary.
- `GET /plan/guides/programs/{program_id}/days/{day_index}`: day drill-down.
- `GET /plan/guides/programs/{program_id}/exercise/{exercise_id}`: exercise drill-down.

### Program selection and switching
- `GET /profile/program-recommendation`: deterministic recommendation and reason.
- `POST /profile/program-switch`: two-step confirmation semantics (`confirm=false` preflight, `confirm=true` apply).

### Error and compatibility policy
- Guide endpoints return `404` for unknown resources.
- Template validation failures surface as `422` with stable error semantics.
- Additive response fields are preferred; breaking field removals/renames require coordinated updates.

## 4) Offline Replay Contract

Scope: deterministic offline queue/replay and sync status semantics.

- Canonical contract document: `docs/Offline_Sync_Deterministic_Contract.md`
- Replay must be idempotent via `(client_id, op_id)` semantics.
- Ordering and conflict resolution behavior must remain deterministic.
- Sync status states/transitions must match the contract state machine.

## 5) Security & Hardening Contract

Scope: secrets handling, rate limiting, backup/restore, and failure drill requirements.

- Canonical contract document: `docs/Security_Hardening_Architecture.md`
- Secrets strategy must enforce runtime-only secret injection and rotation boundaries.
- Rate limiting behavior must return deterministic `429` semantics.
- Backup/restore and failure drills must follow scripted, verifiable procedures.

## 6) Auth Expansion Contract

Scope: OAuth (Google/Apple) and Passkey (WebAuthn) architecture and identity-linking semantics.

- Canonical contract document: `docs/Auth_Expansion_Architecture.md`
- Auth methods are additive and must preserve existing password/JWT flows.
- Identity linking across methods must be deterministic and conflict-safe.
- Auth endpoint error semantics (`401/409/422`) must remain predictable and testable.

## Enforcement Checklist

Before merging changes in these areas:
- Run focused API tests for changed contract surfaces.
- Run web tests/build for affected consumers.
- Update this file and `docs/GPT5_MINI_HANDOFF.md` if any contract boundary changes.



## Progress Sync (2026-03-06)
- Repository state synchronized through commit `18dd81b` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - Remaining warnings are dependency-level (`passlib` `crypt` deprecation and `python-jose` internal `utcnow` deprecation).
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

