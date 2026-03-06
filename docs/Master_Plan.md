# Master Plan (Authoritative, Evidence-Based)

Last updated: 2026-03-06
Audit basis: committed `HEAD` on `main` (unstaged local edits intentionally excluded from this audit)

## Purpose

This file is the single execution plan for product architecture and delivery.
Code + tests + generated artifacts are the source of truth.
If docs conflict with code, docs must be corrected immediately.

## Product Intent (Locked)

Build a deterministic hypertrophy coaching system that:

- Is local-first and self-hostable.
- Uses canonical program data at runtime.
- Adapts schedule/progression with explainable deterministic rules.
- Uses PDF/XLSX sources at build-time only.
- Preserves explicit user confirmation for major plan changes.

## A. Verified Current State

### Platform

- API is FastAPI + SQLAlchemy with Alembic migrations and active tests.
- Web is Next.js App Router with core routes: onboarding, week, today, check-in, history, guides, settings.
- Core engine has deterministic modules for scheduler/progression/warmups/equipment/intelligence.

### Implemented capabilities (verified)

- Deterministic week generation from canonical JSON templates.
- Equipment-aware substitution filtering during generation.
- Soreness-aware deterministic load modifiers.
- Mesocycle/deload signaling from generated week context.
- Workout runner with set logging, live in-session guidance, and day summary.
- Weekly review persistence and adjustment application into next generated week.
- Program recommendation and explicit program-switch confirmation flow.
- Guide APIs for program/day/exercise drill-down.
- Intelligence APIs in committed `HEAD` for:
  - `GET /plan/intelligence/reference-pairs`
  - `POST /plan/intelligence/coach-preview`
  - `POST /plan/intelligence/apply-phase`
  - `POST /plan/intelligence/apply-specialization`

### Known hard gaps (verified)

- Reference guide artifacts in repo are currently metadata-only (`pdf_metadata_only`, `xlsx_metadata_only`), with zero extracted text.
- Imported templates have severe quality variance (many non-workout rows promoted into sessions/exercises).
- Video coverage in templates is near-zero for most imported programs.
- Frontend now consumes intelligence endpoints in Settings, Week, Check-In, and Today (`coach-preview`, `apply-phase`, `apply-specialization`).
- Apply flow auto-chains preview `recommendation_id` across integrated surfaces.
- No first-class coaching decision timeline UX.

## B. Master Plan Corrections

These corrections replace drifted assumptions:

- "All checked items are verified" is invalid. Several prior checks used broad grouped evidence and must be reclassified.
- `programs/schema.py` is referenced in prior audit docs but does not exist.
- "Ingestion complete" must be split:
  - Pairing/catalog/dedup: implemented.
  - Usable extracted manual knowledge: not implemented in committed artifacts.
- "Coaching intelligence complete" must be split:
  - Engine + API backend contracts: mostly implemented in `HEAD`.
  - End-to-end product behavior (UI flow + user decisions + traceability UX): partial.
- "Template library complete" is false for quality:
  - Quantity exists.
  - Many imported templates are structurally noisy and not coach-grade.

## C. Proposed Architecture For Intelligent Program Coaching

1. Source ingestion layer
- Deterministic asset scan, checksum, dedup, workbook/PDF pairing.
- Full extraction mode for PDF/XLSX text and workbook structure.
- Provenance capture at entity level.

2. Knowledge normalization layer
- Canonical entities: program, phase, workout day, exercise slot, rule bundles.
- Rule extraction outputs: progression, deload, transitions, specialization, warmups, constraints.
- Quality gates reject malformed or non-workout rows.

3. Program engine layer
- Selects program by profile + availability + compatibility.
- Adapts schedule while preserving priorities and fatigue balance.
- Computes session order, progression actions, phase transitions, and deload decisions.

4. User performance model
- Tracks planned vs performed outcomes.
- Computes readiness/momentum/stagnation signals.
- Detects weak-point lag patterns from repeated underperformance.

5. Coaching recommendation layer
- Generates explainable recommendations with deterministic rationale.
- Persists recommendation records and supports confirmed apply endpoints.
- Maintains source traceability to template/rule provenance.

6. UI layer
- Presents preview/apply coaching decisions.
- Shows tradeoffs for schedule adaptation.
- Shows phase path, rationale, and exercise videos.

## D. Implementation Phases

### Phase 1: Audit hardening and truth controls

- Rebuild checklist audit with strict evidence mapping.
- Add automated guard that validates evidence file references.
- Require status classes: `VERIFIED`, `PARTIAL`, `NOT VERIFIED`.

Exit criteria:
- Drift checks fail fast in preflight when evidence links are broken.

### Phase 2: Ingestion quality floor

- Promote full-extraction workflow for reference ingestion runs.
- Add deterministic row sanitization in XLSX importer.
- Add template quality checks (session semantics, exercise density, video mapping quality).

Exit criteria:
- Canonical templates pass quality gate.
- Generated guide docs contain meaningful extracted content.

### Phase 3: Canonical model and rule normalization

- Introduce normalized rule structures per program family.
- Encode transitions, deload, specialization, and adaptation rules deterministically.
- Add provenance links from rules to source sections.

Exit criteria:
- Rule bundles are queryable/testable without manual interpretation.

### Phase 4: Engine evolution

- Improve schedule adaptation beyond naive compression.
- Add controlled specialization integration rules.
- Add stronger readiness + fatigue decision matrix.

Exit criteria:
- Scenario tests A-E pass deterministically.

### Phase 5: Coaching UX integration

- Wire frontend to intelligence preview/apply endpoints.
- Add recommendation timeline and rationale surfaces.
- Show adaptation tradeoffs and phase transition explanations.

Exit criteria:
- User can preview, confirm, apply, and review decisions in UI.

### Phase 6: Regression safety and parity

- Expand tests across importer/engine/API/web flows.
- Keep deterministic behavior stable.
- Validate mobile quality/performance.

Exit criteria:
- `mini_validate` + intelligence scenario suites green.

## E. First Files To Inspect / Modify

- `importers/reference_corpus_ingest.py`
- `importers/xlsx_to_program.py`
- `apps/api/app/template_schema.py`
- `apps/api/app/program_loader.py`
- `packages/core-engine/core_engine/intelligence.py`
- `packages/core-engine/core_engine/scheduler.py`
- `apps/api/app/routers/plan.py`
- `apps/web/lib/api.ts`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/week/page.tsx`
- `apps/api/tests/test_reference_corpus_ingestion.py`
- `apps/api/tests/test_plan_intelligence_api.py`
- `packages/core-engine/tests/test_intelligence.py`

## F. Risks And Unknowns

- Source materials may contain implicit rules not directly represented in workbook columns.
- Current template imports include noisy rows that can distort recommendations.
- Unstaged local edits can create apparent drift vs committed `HEAD` truth.
- Full extraction can be environment-sensitive if parser dependencies are missing.

Mitigations:

- Treat committed `HEAD` + passing tests as audit baseline.
- Enforce artifact quality checks before accepting new template imports.
- Keep deterministic logic centralized in engine modules.
- Require provenance-aware rules, not free-form runtime text interpretation.

## G. Initial Code Changes (This Execution)

- Rewrote this plan to reflect committed-repo truth.
- Rebuilt checkmark audit strategy to remove blanket completion claims.
- Added automated audit-evidence verification hook in preflight flow.
- Added deterministic XLSX importer sanitization to filter structural/non-workout rows.
- Added importer regression tests covering row sanitization.
- Added frontend Settings coaching panel wiring for intelligence preview/apply endpoint calls.
- Added frontend tests covering settings coaching preview/apply behavior.

## Runtime Non-Negotiables

- No runtime PDF/XLSX parsing.
- No runtime vector retrieval required for core planning flows.
- Major plan changes require explicit confirmation and explanation.

# Roadmap (Phases + Checklists)

## Phase 1 - Drift Control

- [x] Replace narrative-only master plan with evidence-first plan sections A-G.
- [x] Reclassify audit statuses to `VERIFIED/PARTIAL/NOT VERIFIED`.
- [x] Add audit evidence path validation script.
- [x] Run preflight with audit guard integrated.

## Phase 2 - Ingestion Reality Upgrade

- [x] Add deterministic XLSX row sanitization that excludes non-workout rows.
- [x] Add ingestion quality report (invalid sessions, missing reps/sets, missing video links).
- [ ] Add full-extraction runbook and CI/local mode policy.
- [ ] Regenerate `docs/guides` with non-empty excerpts and verify checksums.

## Phase 3 - Canonical Rule Layer

- [ ] Add normalized rule payload schema for transitions/deload/specialization.
- [ ] Emit provenance links from canonical rules back to source assets.
- [ ] Add tests validating rule extraction determinism.

## Phase 4 - Coaching Engine Hardening

- [ ] Improve schedule adaptation algorithm to preserve movement distribution under compression.
- [ ] Add deterministic weak-point integration policy with fatigue caps.
- [ ] Add scenario tests for A/B/C/D/E product requirements.

## Phase 5 - Product Integration

- [x] Add frontend client contracts for intelligence preview/apply endpoints.
- [x] Add initial Settings recommendation preview/apply UI wiring.
- [x] Build full recommendation preview/apply UX across week/check-in/settings/today.
- [x] Add recommendation timeline UI with rationale visibility.

## Phase 6 - Validation + Release Gate

- [ ] Expand API and web tests for full coaching loop.
- [ ] Run `./scripts/mini_validate.sh` with all new tests passing.
- [ ] Update docs and audit with final evidence references.

## Definition Of Done

An item is complete only when:

- Code is merged.
- Deterministic tests cover behavior.
- Evidence references are valid and resolvable.
- This file and `docs/Master_Plan_Checkmark_Audit.md` are updated.

