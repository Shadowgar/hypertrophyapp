# Master Plan - Adaptive Coaching Rebuild

Last updated: 2026-03-06

## Product Vision

Rocco's HyperTrophy is a true adaptive hypertrophy coaching platform.

It must behave like a coach, not a document parser.

User outcomes:
- Choose a program
- Run daily workouts with videos, warmups, work sets, and targets
- Log reps/weight/notes
- Get deterministic performance evaluation
- Get adaptive future prescriptions based on history, fatigue, adherence, and stalls

## Source-Of-Truth Rules

1. Excel spreadsheets are the primary structured program source.
2. PDF manuals are the primary coaching doctrine source.
3. Runtime must not depend on raw PDF/XLSX parsing or text dumps.

## Target Runtime Layers

1. Program Template Layer
2. Coaching Rules Layer
3. Exercise Knowledge Layer
4. User Training State Layer
5. Decision Engine
6. Product UI/API Layer

Build-time pipelines may parse source files; runtime may not.

## Current Critical Gap

The repository currently still contains ingestion-centered artifact generation (`docs/guides/generated/*.md` excerpts) that is useful for provenance checks but not sufficient as runtime coaching logic.

## Ordered Execution Plan (Do In Order)

### Phase A - Architecture Audit and Isolation
- [x] Audit and classify ingestion-centered code into keep/isolate/deprecate/delete.
- [x] Remove any runtime coupling to guide text artifacts.
- [x] Publish explicit deprecation/isolation list.

### Phase B - Canonical Schema and Gold Baseline
- [ ] Finalize canonical schema for program templates, exercise catalog, coaching rules, user logs/state.
- [ ] Create one manually validated gold sample (workbook + matching PDF doctrine).
- [ ] Add strict schema validation tests and ambiguity/error reporting.

### Phase C - Importer and Rule Distillation
- [ ] Implement Excel-first canonical importer v2 (phase/week/day/slot fidelity).
- [ ] Implement PDF-to-rules distillation workflow (typed rules, explainable rationale).
- [ ] Add provenance links from rules to source sections.

### Phase D - Deterministic Decision Engine
- [ ] Implement first-pass deterministic progression and adaptation logic for gold sample.
- [ ] Model fatigue, underperformance, stalls, deload triggers, and substitutions.
- [ ] Persist explainable decision rationale on each adjustment.

### Phase E - Gold End-To-End Runtime Flow
- [ ] Program selection
- [ ] Workout generation
- [ ] Performance logging
- [ ] Workout evaluation
- [ ] Next-workout adaptation

### Phase F - Scale and Harden
- [ ] Expand canonical imports/rules beyond gold sample.
- [ ] Strengthen scenario tests and regression safety.
- [ ] Close release gate with evidence-backed docs and green validation.

### Phase G - Onboarding Reliability and Parity
- [x] Add developer-safe account reset controls directly in onboarding for local test loops.
- [x] Add actionable auth failure handling with explicit recovery paths.
- [ ] Review external onboarding references and translate into concrete parity tasks (copy, flow steps, friction points).
- [ ] Implement onboarding funnel refinements (step sequencing, progress indicator, and reduced cognitive load).

## Non-Negotiables

- No runtime PDF/XLSX parsing
- No chatbot-only coaching logic
- No claims of intelligence without deterministic rule evidence
- No silent importer guessing on ambiguous structure

## Primary Design Reference

- `docs/redesign/Adaptive_Coaching_Redesign.md`
- `docs/redesign/Architecture_Audit_Matrix.md`
- `docs/redesign/Program_Onboarding_Architecture_Phase1.md`
- `programs/gold/adaptive_full_body_gold_v0_1.json`
- `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json`

## Current Delivery Delta

- Runtime program catalog now excludes legacy `*_imported.json` artifacts and serves canonical templates only.
- User weak areas are persisted on profile and used as defaults in adaptation workflows.
- Deterministic adaptation preview API now supports `2/3/4/5` target training days:
	- `POST /plan/adaptation/preview`
- Deterministic adaptation apply path now feeds runtime week generation:
	- `POST /plan/adaptation/apply`
	- `POST /plan/generate-week` consumes active adaptation state and decrements temporary duration week-by-week.
- Onboarding testing reliability improvements:
	- `POST /auth/dev/wipe-user` (dev-only by config) supports wipe-by-email reset when register/login is blocked by stale test accounts.
	- Onboarding screen now includes explicit `Wipe Test User By Email` and `Wipe Current Logged-In User Data` controls.
