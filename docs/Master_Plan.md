# Master Plan - Adaptive Coaching Rebuild

Last updated: 2026-03-16

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

The main product bottleneck is no longer generic architecture cleanup.

The current bottleneck is finishing one real administered program path around Pure Bodybuilding Phase 1 Full Body.

Current branch reality:
- the workbook-faithful Phase 1 onboarding package now exists as a rich authoritative artifact
- runtime/API week-generation and today-session paths now carry the authored slot fields through
- week/today UI now shows those authored execution details directly
- the live administered full-body identity is now unified on `pure_bodybuilding_phase_1_full_body` with legacy aliases handled for compatibility
- a canonical end-to-end API smoke path now verifies identity/continuity through generate-week, today/log-set, check-in/review, history, adaptation apply, and regenerate-week
- the next product seam after identity unification is end-to-end dogfooding of this administered Phase 1 path

Current product order for active implementation is:
1. workbook-faithful Pure Bodybuilding Phase 1 package
2. runtime/API carry-through of authored fields
3. visible week/today authored execution detail
4. only then program-specific temporary frequency adaptation

Immediate direction:
- keep one-program-first as the primary delivery track
- preserve explicit schemas, deterministic rules, and structured traces on the Phase 1 path
- keep broader architecture cleanup subordinate unless it directly blocks the administered Phase 1 runtime

## Active Operating Mode (One Program First)

Current active product mode is one-program-first.

- `pure_bodybuilding_phase_1_full_body` is the only active administered program exposed on normal user catalog/selection flows.
- `full_body_v1` and `adaptive_full_body_gold_v0_1` remain compatibility aliases for stored state, legacy links, and explicit compatibility tests.
- Other templates (for example `ppl_v1`, `upper_lower_v1`) remain in-repo library/future assets, but are not equal active product choices during this phase.

Current execution order:
1. maintain the workbook-faithful Pure Bodybuilding Phase 1 package
2. keep authored slot fields carried through runtime/API without flattening
3. keep week/today rendering authored execution detail directly
4. keep `pure_bodybuilding_phase_1_full_body` as the single administered identity, with `full_body_v1` and `adaptive_full_body_gold_v0_1` as compatibility aliases only
5. dogfood the full administered Phase 1 path end-to-end on desktop/mobile browser
6. only then resume broader `intelligence.py`, coaching-state, and SFR cleanup where it directly helps the active product path

## Local Dogfood Loop (Canonical Path)

Use this repeatable local loop for one-program-first verification:

1. Log in with a local test account.
2. Reset current account to clean Phase 1 state:
   - `POST /profile/dev/reset-phase1`
   - or use onboarding Developer Tools: `Reset Current User to Clean Phase 1`.
3. Generate week (`POST /plan/generate-week`).
4. Open Today page (workout auto-loads when API health OK; same soreness/review gate as Load Today Workout) and verify authored execution detail is present.
5. Log a set (`POST /workout/{session_id}/log-set`).
6. Submit weekly check-in/review (`POST /weekly-checkin`, `POST /weekly-review`).
7. Verify history (`GET /history/calendar`).
8. Apply temporary frequency adaptation (`POST /plan/adaptation/apply`), regenerate week, verify canonical continuity.

## Ordered Execution Plan (Do In Order)

### Phase A - Architecture Audit and Isolation
- [x] Audit and classify ingestion-centered code into keep/isolate/deprecate/delete.
- [x] Remove any runtime coupling to guide text artifacts.
- [x] Publish explicit deprecation/isolation list.

### Phase B - Canonical Schema and Gold Baseline
- [x] Finalize canonical schema for program templates, exercise catalog, coaching rules, user logs/state (in use for Phase 1 path).
- [x] Create one manually validated gold sample (workbook + matching PDF doctrine) — Pure Bodybuilding Phase 1 Full Body package and gold runtime.
- [x] Add strict schema validation tests and ambiguity/error reporting. Implemented: `apps/api/tests/test_schema_validation.py`.

### Phase C - Importer and Rule Distillation
Design documents exist; core v2 pipelines implemented; provenance links require manual curation pass.
- [x] Implement Excel-first canonical importer v2 (phase/week/day/slot fidelity). Implemented: `importers/xlsx_to_canonical_v2.py`. Design: `docs/plans/2026-03-16-importer-v2-design.md`.
- [x] Implement PDF-to-rules distillation workflow (typed rules, explainable rationale). Implemented: `importers/pdf_doctrine_rules_v2.py`. Design: `docs/plans/2026-03-16-pdf-to-rules-design.md`.
- [ ] Add provenance links from rules to source sections (requires manual curation pass over extracted rules).

### Phase D - Deterministic Decision Engine
- [x] Establish one sovereign decision runtime in `packages/core-engine` for all meaningful coaching decisions.
- [x] Emit structured decision traces for each decision family.
- [x] Refactor router-owned coaching heuristics behind interpreter paths.
- [x] Collapse `intelligence.py` from mixed owner/compatibility hub into a thin façade over explicit decision families.
- [x] Implement first-pass deterministic progression and adaptation logic for gold sample.
- [x] Expand coaching state beyond adherence/soreness/stalls to include higher-signal readiness and constraint inputs.
- [x] Add deterministic stimulus-fatigue-response scoring on top of canonical state and rules runtime.
- [x] Model fatigue, underperformance, stalls, deload triggers, and substitutions.
- [x] Persist explainable decision rationale on each adjustment (traces on generated-week, coach-preview, review, etc.).

### Phase E - Gold End-To-End Runtime Flow
- [x] Program selection
- [x] Workout generation
- [x] Performance logging
- [x] Workout evaluation
- [x] Next-workout adaptation

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
- [docs] [Onboarding Engine Roadmap](docs/implementation/ONBOARDING_ENGINE_ROADMAP.md): Phase 1 (constraints_only) exit criteria = onboarding persists `equipment_profile`, `session_time_budget_minutes`, and `movement_restrictions` and generate-week honors both the time-budget cap and restricted movement filtering.

Reference:
- `docs/redesign/Onboarding_Reference_Analysis_Batch1.md`

### Phase H - User Testing Readiness
- [x] Finish one stable, user-testable deterministic gold runtime path on the web product.
- [ ] Validate onboarding, generate-week, today, log-set, weekly-review, and history on desktop and mobile browser viewports (use `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md`).
- [ ] Run internal dogfooding before any broader beta.
- [ ] Expand to closed beta only after deterministic traces and support/debugging workflows are good enough to explain coaching behavior.

Reference:
- `docs/archive/plans/2026-03-11-user-testing-rollout-plan.md`

## Non-Negotiables

- No runtime PDF/XLSX parsing
- No chatbot-only coaching logic
- No claims of intelligence without deterministic rule evidence
- No silent importer guessing on ambiguous structure

## Primary Design Reference

- `docs/redesign/Adaptive_Coaching_Redesign.md`
- `docs/redesign/Architecture_Audit_Matrix.md`
- `docs/redesign/Program_Onboarding_Architecture_Phase1.md`
- `programs/gold/pure_bodybuilding_phase_1_full_body.json` (active administered program template)
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` (active onboarding package)
- `docs/rules/canonical/pure_bodybuilding_phase_1_full_body.rules.json` (active canonical rules)
- `programs/gold/adaptive_full_body_gold_v0_1.json` (compatibility baseline)
- `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json` (compatibility baseline rules)

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
- The Phase 1 canonical program now owns the live runtime loader path:
	- `apps/api/app/program_loader.py` resolves `pure_bodybuilding_phase_1_full_body` as the primary runtime template source.
	- compatibility aliases (`full_body_v1`, `adaptive_full_body_gold_v0_1`) normalize to that canonical source at loader boundaries.
	- canonical rules load first, with legacy gold-rule scheduler overlay used only as compatibility fallback when canonical scheduler blocks are absent.
- Pure Bodybuilding Phase 1 Full Body is now the first source-backed rich onboarding package on the branch:
	- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` explicitly preserves authored slot fields, top-level notes/warm-up/weak-point sections, week labels, block labels, special banners, and workbook-backed video links.
	- the runtime loader/API path now carries those authored execution fields into generated-week and today workout exercises.
	- week/today surfaces now show early-set RPE, last-set RPE, last-set intensity technique, rest, authored substitutions, and demo links directly from the authoritative package/runtime data.
- Today page auto-loads the workout on mount when API health is OK (same soreness/review gate as Load Today Workout); a guard prevents double-invoke; when no week exists, the recovery action (Generate Week and Reload Today) is shown.
- Canonical administered-path hardening now includes user-facing fixture/snapshot truth:
	- API and web path-facing tests now default to `pure_bodybuilding_phase_1_full_body` as the primary administered identity.
	- legacy IDs remain in explicit compatibility coverage only.
- Canonical administered-path hardening now includes explicit end-to-end smoke verification:
	- `apps/api/tests/test_phase1_canonical_path_smoke.py` validates the canonical flow through onboarding, generate-week, today/log-set, weekly check-in/review, history, adaptation apply, regenerate-week, and training-state continuity.
	- compatibility aliases are still verified separately and explicitly (`full_body_v1`, `adaptive_full_body_gold_v0_1`), not used as the primary proof path.
- The adaptive gold sample is now a real authored mesocycle instead of a short proof stub:
	- `programs/gold/adaptive_full_body_gold_v0_1.json` now follows a 10-week authored sequence aligned to the onboarding package cadence: `build_a / build_b / build_a / build_b / build_a / deload / intens_a / intens_b / intens_a / intens_b`.
	- runtime loader contracts preserve all 10 authored weeks with explicit `week_role` values and a five-day authored source (`Full Body #1-#4` plus `Arms & Weak Points`) rather than the earlier compressed three-day surrogate.
	- generated-week compression now starts from that five-day authored truth and preserves both the dedicated weak-point/arms day and all primary compound movement patterns when adapting downward.
	- generate-week now proves week-6 authored deload plus later intensification-week selection on the gold runtime path.
	- post-week-10 behavior is now explicit: generated-week holds the final authored week as the deterministic fallback while surfacing `authored_sequence_complete` and `phase_transition_pending` in `mesocycle`.
	- that same post-week-10 signal now propagates through canonical training state and downstream coaching layers: coach-preview can explicitly tell the user the authored mesocycle is complete and recommend rotating programs, and program recommendation now treats authored-sequence completion as a first-class rotation trigger instead of a hidden scheduler-only flag.
	- the next fidelity step after identity unification is end-to-end dogfooding of the canonical administered Phase 1 path before broader user testing or wider library migration.
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
	- `./scripts/mini_validate.sh` runs API tests (docker or, when docker is unavailable, local `pytest` or `python3 -m pytest` if `pytest` is not on PATH), then web tests and web build.
- User-testing rollout now has an explicit plan:
	- internal dogfooding should begin on the responsive web app first, using desktop and mobile browsers rather than waiting for native mobile apps.
	- beta readiness and rollout sequencing now live in `docs/archive/plans/2026-03-11-user-testing-rollout-plan.md`.
- Today page redesign (mobile-first, iOS-ready) implemented:
	- design: whole-day list at a glance, tap exercise to open detail screen; Session Intent and Between-Set Coach removed from main view; single “Do this set” line from API guidance only (`resolveGuidanceText`).
	- design doc: `docs/plans/2026-03-15-today-page-redesign-design.md`. Implementation complete; see `docs/implementation/ACTIVE_REMEDIATION_RAIL.md` § Done: Today Page Redesign.
