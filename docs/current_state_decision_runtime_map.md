# Current-State Decision Runtime Map

Last updated: 2026-03-13

## Purpose

This document is the current operational ownership map for the deterministic coaching runtime.

Use it to answer these questions before changing code:

1. Which module is authoritative for this decision family?
2. What canonical inputs should it consume?
3. What outputs and traces should it emit?
4. What, if anything, should remain in `packages/core-engine/core_engine/intelligence.py`?
5. What may still happen in routers?

This document is current-state truth. Historical handoff docs are evidence logs, not ownership maps.

## Current Strategic Read

Router glue is no longer the dominant architectural risk.

Current product-critical path is no longer generic architecture cleanup.

Current branch reality is:
- the [Pure Bodybuilding Phase 1 onboarding package](/home/rocco/hypertrophyapp/programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json) is now workbook-faithful and structurally rich
- generated-week and today runtime exercises now carry the authored Phase 1 slot fields through the loader/API boundary
- week/today surfaces now render those authored execution details directly
- the live administered full-body identity is now unified to `pure_bodybuilding_phase_1_full_body` with compatibility aliases resolving safely
- the next bounded product seam is end-to-end dogfooding of this real Phase 1 administered path before wider cleanup

Current product order for active implementation is:
1. keep `pure_bodybuilding_phase_1_full_body` as the single administered Phase 1 identity (aliases compatibility-only)
2. dogfood the canonical Phase 1 path end-to-end (onboarding -> generate-week -> today -> log-set -> checkin/review -> history)
3. only then broaden cleanup/generalization work beyond the active program path

Secondary architectural risks still matter, but they are no longer the primary product bottleneck:
- authority ambiguity and historical wrapper drift in [intelligence.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/intelligence.py)
- shallow first-class coaching state in [models.py](/home/rocco/hypertrophyapp/apps/api/app/models.py) beyond canonical `constraint_state`, weekly-checkin-backed `readiness_state`, and persisted coaching-state SFR snapshot
- early-stage stimulus-fatigue-response logic that now affects some decisions but is not yet broadly shared across generation, substitution, and review families
- documentation drift between historical handoff logs and actual local-branch module ownership

## Decision Family Map

| Family | Authoritative Module | Canonical Inputs | Canonical Outputs | Trace Contract | Router Responsibilities | `intelligence.py` Status |
| --- | --- | --- | --- | --- | --- | --- |
| User training state assembly | [user_state.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/user_state.py) | persisted plans, workout logs, `ExerciseState`, soreness, check-ins, reviews, prior plans, persisted profile constraints | canonical `UserTrainingState` payload including `constraint_state`, `readiness_state`, top-level and nested coaching-state `stimulus_fatigue_response`, and `generation_state.latest_mesocycle`, plus plan-decision training-state payloads | explicit `decision_trace` on assembled runtime payloads | SQL fan-in only; response validation | not owner |
| Rules runtime | [rules_runtime.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/rules_runtime.py) | typed canonical rule payloads, exercise/equipment context, performance context, generated-week scheduler inputs derived from canonical templates and canonical user state; generated-week scheduler doctrine now comes from canonical `generated_week_scheduler_rules` plus authored `day_role` / `slot_role` template metadata, explicit authored muscle metadata, canonical `deload_rules`, and upstream `stimulus_fatigue_response_source` trace context | normalized adaptive runtime config, substitution runtime, deload runtime, starting-load runtime, generated-week mesocycle runtime, generated-week exercise-adjustment runtime, generated-week session-selection runtime, generated-week session-cap runtime, generated-week muscle-coverage runtime, generated-week deload-execution runtime | direct decision traces for substitution, starting-load, and generated-week scheduler policy runtimes; mesocycle traces now preserve the consumed SFR source without re-owning SFR derivation | load linked rule set only | not owner |
| Generation template and week-generation runtime | [generation.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/generation.py) | selected template, optional rule set, canonical training state including `progression_state_per_exercise`, profile context, prior review overlay, adaptation context, and adaptive-gold runtime templates when loaded through the program loader | template-selection runtime, coach-preview request runtime, week-generation runtime, finalized generated-week payload prep, movement-pattern filtering from canonical movement restrictions, runtime use of the adaptive gold sample through the loader boundary, adaptive-gold substitution metadata hydrated from the matching onboarding exercise library, authored five-day day-role semantics preserved through canonical template metadata, and source-backed multi-phase authored adaptive bundles flattened into one runtime sequence at the loader boundary | structured `decision_trace` on request shaping, template choice, generation runtime, finalize helpers; finalized generated-week payload traces now surface the scheduler mesocycle `stimulus_fatigue_response_source` at stable top-level trace locations | template/rule loading, SQL reads, DB writes, HTTP mapping | still owns separate generation-template selection logic in `intelligence.py`; should stay isolated to generation domain and not absorb new coaching logic |
| Frequency adaptation | [decision_frequency_adaptation.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_frequency_adaptation.py) | onboarding package, current/target day count, canonical user state derived context, recovery/equipment/weak-area inputs | preview/apply payloads, persistence state, active adaptation runtime/application | explicit `decision_trace` with ordered steps and request runtime provenance | SQL fan-in, onboarding package load, persistence commit | façade/wrapper only |
| Program recommendation and switch | [decision_program_recommendation.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_program_recommendation.py) | current program, available program summaries, days available, split preference, latest plan payload, canonical `UserTrainingState` including `generation_state.latest_mesocycle`, switch target/confirm | candidate-resolution trace, recommendation decision, recommendation response payload, switch response payload, apply gate; explicit authored-sequence rotation when mesocycle completion is already known | explicit traces for candidate resolution, recommendation selection, route runtime, and switch outcome | profile/latest-plan SQL reads, confirmed `selected_program_id` persistence, HTTP mapping | façade/wrapper only |
| Progression, readiness, phase transition, schedule adaptation | [decision_progression.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_progression.py) | completion, adherence, soreness, average RPE, underperformance streaks, rule set, schedule adaptation inputs, canonical `readiness_state` when available, and latest mesocycle transition flags when present | readiness score, progression action, phase transition, schedule adaptation payloads, derived `stimulus_fatigue_response` snapshot; explicit `transition_pending` / `recommended_action` on authored-sequence completion | direct outputs are deterministic but currently do not emit standalone `decision_trace`; parent families such as coach-preview carry trace context and now surface the SFR snapshot plus transition-pending state | none directly; consumed by coach-preview and other engine helpers | façade/wrapper only |
| Weekly review | [decision_weekly_review.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_weekly_review.py) | previous-week plan payload, performed logs, check-in inputs, review window, review-cycle context, canonical `readiness_state` when available, canonical `coaching_state.stimulus_fatigue_response` when available | weekly-review summary, decision payload, submit payload, persistence payloads, status payload, adaptive plan overlays | explicit traces on summary/status/submit/apply helpers, including readiness-state source and weekly-review SFR source when present | SQL reads and ORM writes for checkin/review records, HTTP mapping | façade/wrapper only |
| Coach preview, apply, recommendation timeline | [decision_coach_preview.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_coach_preview.py) | canonical user state, preview request, selected template, rule set, recommendation rows, apply confirm/source recommendation, weekly volume by muscle, lagging muscles, template media/warmup data, latest mesocycle transition flags, canonical `coaching_state.stimulus_fatigue_response` context | preview payloads, specialization recommendation payloads, media/warmup summary, record fields, apply runtime/commit/finalize payloads, timeline entries/payloads; preview-visible authored-sequence completion guidance | explicit traces on preview, apply, finalize, and timeline helpers; coach-preview traces surface persisted canonical SFR context separately from the request-time progression snapshot, while specialization/media builders remain deterministic without standalone traces | SQL reads, template/rule loading, DB writes, HTTP mapping | façade/wrapper only |
| Workout route-runtime orchestration | [decision_workout_session.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_workout_session.py) | plan context runtime, log runtime, session-state runtime, workout summary runtime, progression lookup runtime, workout logs, progression states, planned exercise context, `ExerciseState` rows | route-ready payloads for `today`, `progress`, `summary`, `log-set`, session-state upsert, response hydration, workout performance summary, log-set request/runtime payloads, session-state defaults/persistence payloads, repeat-failure substitution payloads | explicit traces with linked sub-traces from lower-level helpers | SQL/ORM reads and writes, optional rule-set loading, HTTP mapping | façade/wrapper only |
| Live workout guidance and set feedback | [decision_live_workout_guidance.py](/home/rocco/hypertrophyapp/packages/core-engine/core_engine/decision_live_workout_guidance.py) | planned rep range, performed reps/weight/set index, rule set, session progress, planned/completed set counts | per-set feedback, live recommendation, hydrated guidance payloads, session-state update guidance, overall session guidance, humanized rationale | explicit traces on `interpret_workout_set_feedback`, `recommend_live_workout_adjustment`, `hydrate_live_workout_recommendation`, and `summarize_workout_session_guidance` | no direct router logic; consumed by workout decision/runtime helpers | façade/wrapper only |

## Current Rule For `intelligence.py`

`intelligence.py` is no longer allowed to grow as a catch-all decision module.

Acceptable uses:
- stable compatibility wrappers over already-extracted decision families
- small cross-family adapters where one decision family injects another as a dependency
- temporary ownership of still-unextracted families explicitly listed in this document

Unacceptable uses:
- adding new decision families
- rebuilding router-local heuristics inside wrapper code
- duplicating logic that already has an authoritative module elsewhere

## Immediate Coding Contract

The current cleanup contract is:

1. keep `decision_live_workout_guidance.py` as the only owner for live workout guidance and set-feedback logic
2. keep only thin compatibility wrappers in `intelligence.py`
3. treat canonical `constraint_state`, `readiness_state`, and `coaching_state.stimulus_fatigue_response` as the shared state contracts for downstream decision families that need persisted recovery-pressure context
4. do not add new coaching logic back into `intelligence.py`
5. preserve deterministic behavior and `decision_trace` contracts while downstream callers are rewired
6. keep adaptive gold runtime support at the loader boundary rather than introducing parallel router-side gold-template handling
7. treat `generation_state.latest_mesocycle` as the canonical bridge between generated-week mesocycle output and downstream coach/program-rotation decisions

## Next Phases After That

After the current seams-0-to-3 one-program-first wave:

1. dogfood the Phase 1 administered path end to end on desktop/mobile browser with authored workout details and decision traces visible
2. fix any branch-truth drift found during dogfooding on the canonical `pure_bodybuilding_phase_1_full_body` path
3. only then keep shrinking remaining mixed-owner seams in `intelligence.py` and broaden SFR/coaching-state consumption where those changes directly support active product behavior
