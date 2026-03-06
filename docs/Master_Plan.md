# Master Plan (Reality-Corrected)

Last updated: 2026-03-06
Owner: HyperTrophy core team
Scope: Monorepo-wide product, architecture, and delivery plan

## Purpose

This is the single authoritative plan for what exists, what is partially implemented, and what must be built next.
Code and tests are the source of truth. If this file conflicts with code, update this file.

## Product Intent

Build a deterministic hypertrophy coaching system that:

- Runs local-first (self-hosted)
- Uses canonical templates at runtime (no runtime PDF/XLSX parsing)
- Delivers explainable scheduling, progression, phase transitions, and specialization guidance
- Preserves user control for all major plan changes

## Verified Current State

### Platform and runtime

- API: FastAPI + SQLAlchemy + Alembic is live and tested.
- Web: Next.js app routes for onboarding, week/today/check-in/history/settings are present.
- Engine: deterministic scheduler/progression/warmup/equipment modules are present.
- Auth: register/login/password reset contract exists.

### Working capability blocks

- Deterministic week generation from canonical `programs/*.json` templates.
- Equipment-aware substitutions and soreness-sensitive load adjustments.
- Mesocycle and deload signaling in generated plans.
- In-session workout logging and deterministic next-step guidance.
- Weekly review cycle with adjustment payload persisted and applied.
- Program recommendation and explicit switch confirmation flow.
- Program guide read endpoints for programs/days/exercises.

### New implementation in this cycle

- Added deterministic intelligence module in `packages/core-engine/core_engine/intelligence.py` with:
  - schedule adaptation + tradeoff reporting
  - progression action recommendation (`progress`, `hold`, `deload`)
  - phase transition recommendation
  - specialization adjustment recommendation
  - media and warmup coverage summary
- Added API endpoints:
  - `GET /plan/intelligence/reference-pairs`
  - `POST /plan/intelligence/coach-preview`
- Added test coverage:
  - `packages/core-engine/tests/test_intelligence.py`
  - `apps/api/tests/test_plan_intelligence_api.py`
  - pairing override coverage in `apps/api/tests/test_reference_corpus_ingestion.py`

### Known gaps (not complete)

- Ingested guide artifacts currently include metadata-only output in the present workspace state.
- Canonical template quality is inconsistent across imported programs.
- Video link coverage is low in many program templates.
- Frontend does not yet expose a full coaching intelligence UI workflow.
- Runtime does not yet persist a first-class "coach decision timeline" entity.

## Non-Negotiable Runtime Rules

- No runtime PDF/XLSX parsing.
- No runtime vector retrieval requirement for core flows.
- Deterministic outputs from profile + history + canonical templates + deterministic rules.
- All major changes (program switch, phase transition, specialization boosts) require explicit user-visible explanation.

## Capability Matrix

Status legend:

- `[x]` complete and validated
- `[~]` partial
- `[ ]` not started

### Data and ingestion

- `[x]` Deterministic reference catalog/provenance generation
- `[x]` Workbook/PDF pairing with enforcement and dedup support
- `[~]` Full text extraction quality for all reference assets
- `[~]` Canonical program normalization quality across all imported templates

### Planning and adaptation

- `[x]` Deterministic weekly plan generation
- `[x]` Equipment-aware substitutions
- `[x]` Soreness-aware load modifiers
- `[x]` Mesocycle and deload signaling
- `[x]` Schedule adaptation tradeoff engine (new)
- `[~]` Missed-session recovery strategy explanation in user-facing UI

### Progression and phase intelligence

- `[x]` Deterministic set logging and next-weight guidance
- `[x]` Weekly review adjustment application
- `[x]` Progress/hold/deload decision engine (new)
- `[x]` Phase transition decision engine (new)
- `[~]` Persistent timeline of decision rationale per user

### Specialization and weak-point strategy

- `[x]` Weak-point inputs in weekly review workflow
- `[x]` Deterministic specialization adjustment preview engine (new)
- `[~]` End-to-end specialization plan application UX

### Guide and media experience

- `[x]` Program/day/exercise guide endpoints
- `[x]` Video and warmup coverage summary engine (new)
- `[~]` Reliable high video-link coverage across templates
- `[~]` Rich exercise guide rendering beyond baseline API payloads

## Architecture Direction (Target)

### Runtime layers

1. Canonical Program Layer
   - Program templates with normalized sessions/exercises
   - Template metadata including split, days, progression style, and media fields

2. Deterministic Intelligence Layer
   - Schedule adaptation with explicit tradeoffs
   - Progression action engine
   - Phase transition engine
   - Specialization allocator
   - Media and warmup coverage analyzer

3. Coaching API Layer
   - Read endpoints for guidance previews and evidence
   - Write endpoints only when user confirms decisions

4. Product UI Layer
   - Explainable recommendation cards
   - User controls: apply, defer, or decline
   - Rationale visibility for every recommendation

## Phased Delivery Plan

### Phase 1: Truth and quality baseline

- Finalize ingestion mode policy (`metadata-only` vs full extraction) for CI and local workflows.
- Raise canonical template quality floor with deterministic sheet sanitization.
- Add quality checks for required exercise fields and day/session semantics.

Exit criteria:

- Asset catalog/provenance stable in CI.
- Pairing enforcement green.
- Template quality checks pass on target corpus.

### Phase 2: Intelligence runtime foundation

- Land deterministic intelligence modules and API preview endpoints.
- Add request/response contracts and full test coverage.
- Ensure no side effects from preview endpoints.

Exit criteria:

- Preview endpoints deterministic and tested.
- Regression suite green.

### Phase 3: User-applied coaching decisions

- Add persisted coaching decision records.
- Add apply endpoints for approved recommendations.
- Add undo-safe controls where feasible.

Exit criteria:

- User can preview, approve, and apply changes with auditable rationale.

### Phase 4: UX and parity hardening

- Integrate coaching previews in week/check-in/settings surfaces.
- Improve guide readability and exercise-level context.
- Harden mobile interaction and visual consistency.

Exit criteria:

- End-to-end coaching workflow available in UI.
- Mobile acceptance and deterministic behavior checks pass.

## Immediate Backlog (Priority Ordered)

1. Add API tests for edge cases in coach preview (invalid template, low-readiness deload branch, phase edge cases).
2. Add persistent coaching recommendation model and migration.
3. Add apply/confirm endpoints for phase and specialization decisions.
4. Improve imported template sanitization for non-workout rows.
5. Improve video link extraction and mapping completeness.
6. Connect frontend settings/check-in pages to coaching preview endpoint.

## Risks and Mitigations

- Risk: false confidence from docs diverging from code.
  - Mitigation: keep this file code-referenced and update on every major change.
- Risk: noisy generated artifacts in git history.
  - Mitigation: isolate ingestion runs and avoid committing incidental churn.
- Risk: adaptation rules become opaque.
  - Mitigation: keep decision outputs explicit (`action`, `reason`, `risk_level`, deltas).
- Risk: template inconsistency undermines intelligence quality.
  - Mitigation: deterministic template quality gates and regression fixtures.

## Definition of Done for this plan

A roadmap item can be marked complete only when:

- Code is merged.
- Deterministic tests cover the behavior.
- API contracts are documented in code-level schemas.
- This file is updated to reflect final status.





## Progress Sync (2026-03-06)
- Repository state synchronized through commit `3596622` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
  - `cb317d0`: hardened `scripts/mini_validate.sh` with compose command detection and one-shot rebuild/retry fallback for failed containerized API test runs
  - `3596622`: migrated auth stack from `passlib/python-jose` to `bcrypt/PyJWT` in API runtime paths
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - `passlib` and `python-jose` deprecation warnings removed from validation output.
  - `mini_validate` run now reports clean test results without warning spam in the default path.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

