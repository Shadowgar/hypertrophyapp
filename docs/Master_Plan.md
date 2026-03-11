# Master Plan - Adaptive Coaching Rebuild

Last updated: 2026-03-11

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

The main architectural risk is still split-brain hardening, but the shape of the gap has changed.

Router glue is no longer the dominant risk.

Current dominant risks are:
- authority ambiguity and wrapper drift in `packages/core-engine/core_engine/intelligence.py`
- shallow first-class coaching state in persistence and canonical user state
- an early-stage deterministic stimulus-fatigue-response layer that is now live but not yet broadly consumed for bounded adjustment decisions
- documentation drift between historical handoff logs and actual local-branch ownership

Immediate direction:
- keep moving decision families into `packages/core-engine` until `intelligence.py` is a thin façade or only owns explicitly temporary logic
- emit structured decision traces or explicitly document why a family still lacks them
- prevent legacy runtime paths from gaining new coaching behavior
- deepen coaching state before adding broad new product surface area

Current execution order:
1. publish and maintain the current-state decision-runtime authority map
2. extract live workout guidance out of `intelligence.py`
3. reduce `intelligence.py` to façade/wrapper status where possible
4. expand persisted coaching-state signals
5. deepen that contract with readiness and recovery signals
6. add a deterministic stimulus-fatigue-response layer
7. broaden that layer across generation and weekly-review bounded adjustment decisions
8. widen the same pressure family only where richer per-exercise state exists
9. then broaden gold baselines and scenario tests

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
- [ ] Establish one sovereign decision runtime in `packages/core-engine` for all meaningful coaching decisions.
- [ ] Emit structured decision traces for each decision family.
- [ ] Refactor router-owned coaching heuristics behind interpreter paths.
- [ ] Collapse `intelligence.py` from mixed owner/compatibility hub into a thin façade over explicit decision families.
- [ ] Implement first-pass deterministic progression and adaptation logic for gold sample.
- [ ] Expand coaching state beyond adherence/soreness/stalls to include higher-signal readiness and constraint inputs.
- [ ] Add deterministic stimulus-fatigue-response scoring on top of canonical state and rules runtime.
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
- [x] Deliver calendar training history view (click past dates to inspect performed exercises and plan deltas).

### Phase G - Onboarding Reliability and Parity
- [x] Add developer-safe account reset controls directly in onboarding for local test loops.
- [x] Add actionable auth failure handling with explicit recovery paths.
- [x] Review external onboarding references (batch 1) and translate into concrete parity tasks.
- [x] Implement onboarding funnel refinements (step sequencing, progress indicator, and reduced cognitive load).

Reference:
- `docs/redesign/Onboarding_Reference_Analysis_Batch1.md`

### Phase H - User Testing Readiness
- [ ] Finish one stable, user-testable deterministic gold runtime path on the web product.
- [ ] Validate onboarding, generate-week, today, log-set, weekly-review, and history on desktop and mobile browser viewports.
- [ ] Run internal dogfooding before any broader beta.
- [ ] Expand to closed beta only after deterministic traces and support/debugging workflows are good enough to explain coaching behavior.

Reference:
- `docs/plans/2026-03-11-user-testing-rollout-plan.md`

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
- Canonical onboarding schema contracts are stricter:
	- onboarding package `program_id` must align across package, blueprint, and intent.
	- week-sequence entries must map to declared week-template IDs.
	- day slot IDs and order indices are validated as unique per day.
- Transitional XLSX importer is less lossy and less silent:
	- emitted templates retain `source_workbook` provenance.
	- workbook parsing now emits explicit `import_diagnostics` warnings for missing headers/prescriptions, structural-label skips, and defaulted session grouping.
- Deterministic adaptation preview API now supports `2/3/4/5` target training days:
	- `POST /plan/adaptation/preview`
- Canonical coaching constraint state has started to land:
	- `User` now persists session time budget, movement restrictions, and near-failure tolerance.
	- canonical `UserTrainingState` now includes `constraint_state`.
	- `/profile` and `/profile/training-state` expose the same normalized constraint fields for downstream decision families.
- Weekly-checkin-backed readiness state has started to land:
	- `WeeklyCheckin` now persists sleep quality, stress level, and pain flags.
	- canonical `UserTrainingState` now includes `readiness_state`.
	- `/profile/training-state` exposes derived readiness risk flags for downstream decision families.
- Coach-preview now consumes canonical `readiness_state` when no explicit `readiness_score` is provided:
	- poor sleep, high stress, and pain flags now lower deterministic readiness in that preview path.
	- the coach-preview trace records whether readiness came from the request, canonical context, or raw request metrics only.
- Weekly-review now also consumes canonical `readiness_state` from the latest persisted check-in:
	- poor sleep, high stress, and pain flags now lower deterministic readiness in the weekly-review path.
	- the weekly-review trace records readiness-state penalty source and matched rules.
- The first deterministic stimulus-fatigue-response layer now exists in the progression family:
	- progression decisions emit a derived `stimulus_fatigue_response` snapshot.
	- coach-preview traces carry that snapshot end-to-end without changing router contracts yet.
	- progression can now deload when that snapshot shows high deload pressure plus low recoverability.
	- weekly-review guidance now also uses the same snapshot to suppress push-style guidance when recovery is clearly limited.
- Deterministic adaptation apply path now feeds runtime week generation:
	- `POST /plan/adaptation/apply`
	- `POST /plan/generate-week` consumes active adaptation state and decrements temporary duration week-by-week.
- The adaptive gold sample now participates in a live runtime loader path:
	- `apps/api/app/program_loader.py` lists `adaptive_full_body_gold_v0_1` in the runtime catalog.
	- the loader adapts `programs/gold/adaptive_full_body_gold_v0_1.json` into the current runtime template contract.
	- the same loader boundary resolves `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json` when canonical rules do not already contain that program scope.
- The adaptive gold sample is now a real authored mesocycle instead of a short proof stub:
	- `programs/gold/adaptive_full_body_gold_v0_1.json` now follows a 10-week authored sequence aligned to the onboarding package cadence: `build_a / build_b / build_a / build_b / build_a / deload / intens_a / intens_b / intens_a / intens_b`.
	- runtime loader contracts preserve all 10 authored weeks with explicit `week_role` values.
	- generate-week now proves week-6 authored deload plus later intensification-week selection on the gold runtime path.
	- post-week-10 behavior is now explicit: generated-week holds the final authored week as the deterministic fallback while surfacing `authored_sequence_complete` and `phase_transition_pending` in `mesocycle`.
	- that same post-week-10 signal now propagates through canonical training state and downstream coaching layers: coach-preview can explicitly tell the user the authored mesocycle is complete and recommend rotating programs, and program recommendation now treats authored-sequence completion as a first-class rotation trigger instead of a hidden scheduler-only flag.
- Onboarding testing reliability improvements:
	- `POST /auth/dev/wipe-user` (dev-only by config) supports wipe-by-email reset when register/login is blocked by stale test accounts.
	- Onboarding screen now includes explicit `Wipe Test User By Email` and `Wipe Current Logged-In User Data` controls.
	- Auth endpoints now resolve email case-insensitively with whitespace normalization (register/login/password reset/dev wipe).
	- Onboarding now includes `Request Password Reset Token` recovery action for deterministic local test loops.
	- Onboarding questionnaire now auto-saves/restores browser-local draft progress with explicit `Clear Saved Draft` control.
- Onboarding funnel parity v1 implemented:
	- intro slides -> step-based questionnaire -> account creation -> deterministic plan bootstrap handoff.
	- profile now persists `onboarding_answers` JSON for richer onboarding signal capture.
- Calendar history view delivered:
	- `GET /history/calendar` exposes clickable daily summaries, program/muscle metadata, and PR badge metadata for a date window.
	- `GET /history/day/{day}` exposes performed workout/exercise/set detail and planned-vs-performed set deltas for selected date.
	- Missed days with planned sessions now return planned-only detail (zero logged sets).
	- `/history` now renders week/month windows, older-window navigation, completion/program/muscle filters, previous-same-weekday jump, same-weekday delta cards, PR badges, and selected-day detail panel.
- Validation gate health:
	- `./scripts/mini_validate.sh` currently passes (`API 85 passed`, `web tests 28 passed`, `web build success`).
- User-testing rollout now has an explicit plan:
	- internal dogfooding should begin on the responsive web app first, using desktop and mobile browsers rather than waiting for native mobile apps.
	- beta readiness and rollout sequencing now live in `docs/plans/2026-03-11-user-testing-rollout-plan.md`.
