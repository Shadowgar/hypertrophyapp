# GPT-5-mini Execution Backlog - Adaptive Coaching Rebuild

Last updated: 2026-03-11

## Priority 0 - Foundation (In Progress)

### Task 0.5 - Decision Runtime Sovereignty
- Move meaningful coaching decisions behind one authoritative interpreter path in `packages/core-engine`.
- Emit structured decision traces.
- Prevent legacy runtime paths from receiving new coaching behavior.
- Status: STARTED

Evidence (2026-03-07)
- `docs/archive/ai-handoffs/AI_CONTINUATION_GOVERNANCE.md`: repository law for decision-runtime sovereignty, legacy containment, and trace requirements.
- `apps/api/app/routers/profile.py` and `packages/core-engine/core_engine/intelligence.py`: program recommendation is the first decision family being migrated behind a core-engine interpreter with a structured decision trace.

Direction Lock (2026-03-10)
- Router glue is no longer the dominant risk.
- `docs/current_state_decision_runtime_map.md` is now the operational current-state authority source for local-branch decision ownership; prefer it over stale public-branch or historical handoff assumptions.
- Current dominant risks are:
  - authority ambiguity and wrapper drift in `packages/core-engine/core_engine/intelligence.py`
  - shallow first-class coaching state in `apps/api/app/models.py`
  - an early-stage deterministic stimulus-fatigue-response layer that is now live but not yet broadly consumed for bounded adjustment decisions
  - documentation drift between historical evidence logs and actual local-branch ownership
- Immediate coding target:
  - keep shrinking mixed-owner seams in `packages/core-engine/core_engine/intelligence.py` where they block coaching-state or SFR work outside the now-façade-only workout family, while extending generated-week pressure only from existing persisted state, canonical constraints, and deterministic template metadata
- Do not add broad new product features before the following sequence is complete:
  1. `docs/current_state_decision_runtime_map.md`
  2. live workout guidance extraction out of `intelligence.py`
  3. first-class coaching constraint state
  4. weekly-checkin-backed readiness/recovery state
  5. deterministic SFR scoring

Evidence (2026-03-10, live workout guidance extraction)
- `packages/core-engine/core_engine/decision_live_workout_guidance.py`: new decision-family owner now centralizes feedback interpretation, in-session adjustment recommendation, hydrated live guidance payloads, session-state guidance updates, and session-guidance summaries.
- `packages/core-engine/core_engine/intelligence.py`: live workout guidance helpers now delegate to thin compatibility wrappers over the dedicated decision-family module instead of owning real logic directly.
- `packages/core-engine/tests/test_decision_live_workout_guidance.py`: focused owner-module regression coverage proves the new decision-family boundary and preserves the prior guidance/trace behavior.
- `packages/core-engine/tests/test_intelligence.py`: compatibility-wrapper regressions remain green for live workout guidance, session-state update, and session-guidance summary paths.
- `apps/api/tests/test_workout_logset_feedback.py`, `apps/api/tests/test_workout_session_state.py`, and `apps/api/tests/test_workout_summary.py`: focused API regressions remained green after the extraction.

Evidence (2026-03-10, coaching constraint state expansion)
- `apps/api/app/models.py` and `apps/api/alembic/versions/0014_user_coaching_constraints.py`: `User` now persists `session_time_budget_minutes`, `movement_restrictions`, and `near_failure_tolerance`.
- `apps/api/app/schemas.py` and `packages/core-engine/core_engine/intelligence.py`: profile upsert/response contracts now accept and emit the new coaching constraint fields with deterministic default shaping.
- `apps/api/app/adaptive_schema.py` and `packages/core-engine/core_engine/user_state.py`: canonical `UserTrainingState` now includes `constraint_state`, and plan-decision training-state helpers now consume the same normalized profile constraint payload.
- `apps/api/app/routers/profile.py`: `GET /profile`, `POST /profile`, and `GET /profile/training-state` now thread the coaching constraint fields through profile persistence and canonical user-state assembly.
- `packages/core-engine/tests/test_user_state.py`, `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_profile_schema.py`, `apps/api/tests/test_user_training_state_schema_contract.py`, `apps/api/tests/test_profile_training_state.py`, `apps/api/tests/test_profile_dev_wipe.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`: focused engine/API regressions passed for the new constraint-state contract.

Evidence (2026-03-10, weekly-checkin readiness state expansion)
- `apps/api/app/models.py` and `apps/api/alembic/versions/0015_weekly_checkin_readiness_fields.py`: `WeeklyCheckin` now persists `sleep_quality`, `stress_level`, and `pain_flags`.
- `apps/api/app/schemas.py` and `packages/core-engine/core_engine/intelligence.py`: weekly-checkin contracts and persistence payload shaping now accept and preserve the new readiness fields.
- `apps/api/app/adaptive_schema.py` and `packages/core-engine/core_engine/user_state.py`: canonical `UserTrainingState` now includes `readiness_state` with derived `recovery_risk_flags`.
- `apps/api/app/routers/profile.py`: `POST /weekly-checkin` now persists the readiness fields, and `GET /profile/training-state` surfaces the derived readiness state.
- `packages/core-engine/tests/test_user_state.py`, `apps/api/tests/test_weekly_checkin.py`, `apps/api/tests/test_user_training_state_schema_contract.py`, `apps/api/tests/test_profile_training_state.py`, `apps/api/tests/test_weekly_review.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`: focused and widened regressions passed for the new readiness-state contract.

Evidence (2026-03-10, readiness-state consumption in coach preview)
- `packages/core-engine/core_engine/decision_progression.py`: `derive_readiness_score` now accepts optional `sleep_quality`, `stress_level`, and `pain_flags`, applying deterministic readiness penalties for poor sleep, high stress, and active pain flags.
- `packages/core-engine/core_engine/generation.py` and `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview context now carries canonical `readiness_state`, and the preview interpreter now uses it when the request omits `readiness_score`.
- `packages/core-engine/tests/test_decision_progression.py`, `packages/core-engine/tests/test_decision_coach_preview.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused engine/API regressions now verify readiness penalties and coach-preview consumption of canonical readiness state.

Evidence (2026-03-10, readiness-state consumption in weekly review)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review decisions now accept canonical `readiness_state`, apply deterministic readiness penalties, and trace the readiness-state source plus matched rules.
- `apps/api/app/routers/profile.py`: weekly-review submit now builds canonical decision training state and passes `readiness_state` into the weekly-review decision family before persistence.
- `packages/core-engine/tests/test_decision_weekly_review.py` and `apps/api/tests/test_weekly_review.py`: focused engine/API regressions now verify weekly-review readiness penalties from the latest persisted check-in.

Evidence (2026-03-10, first deterministic SFR layer)
- `packages/core-engine/core_engine/decision_progression.py`: the progression family now emits a derived `stimulus_fatigue_response` snapshot covering stimulus quality, fatigue cost, recoverability, progression eligibility, deload pressure, and substitution pressure.
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview now forwards canonical readiness inputs into progression scoring, and the progression trace step carries the SFR snapshot end-to-end.
- `packages/core-engine/tests/test_decision_progression.py`, `packages/core-engine/tests/test_decision_coach_preview.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused engine/API regressions now verify both the SFR classification itself and its presence in coach-preview traces.

Evidence (2026-03-10, SFR now affects real decisions)
- `packages/core-engine/core_engine/decision_progression.py`: progression decisions now deload when SFR indicates both high deload pressure and low recoverability, instead of leaving that state as trace-only context.
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review guidance now uses the SFR snapshot to force recovery-limited guidance when recovery is clearly constrained.
- `packages/core-engine/tests/test_decision_progression.py`, `packages/core-engine/tests/test_decision_weekly_review.py`, and `apps/api/tests/test_weekly_review.py`: focused engine/API regressions now verify the SFR-driven behavior changes.

Evidence (2026-03-10, SFR now bounds weekly-review adjustment payloads)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review now applies recovery-limited global set/load adjustments and suppresses positive progression or weak-point boost overrides when SFR shows constrained recoverability.
- `packages/core-engine/tests/test_decision_weekly_review.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_weekly_review.py`: focused engine/wrapper/API regressions now verify the new bounded-adjustment behavior and the persisted no-boost outcome.

Evidence (2026-03-10, generated-week movement restrictions)
- `packages/core-engine/core_engine/generation.py` and `packages/core-engine/core_engine/scheduler.py`: canonical `constraint_state.movement_restrictions` now flow through plan-generation runtime into generated-week scheduling, where exercises with deterministic restricted `movement_pattern` values are filtered out during session construction.
- `packages/core-engine/tests/test_generation.py`, `packages/core-engine/tests/test_scheduler.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine and API regressions passed for movement-restriction filtering from persisted profile state.

Evidence (2026-03-10, generated-week session time budget)
- `packages/core-engine/core_engine/generation.py` and `packages/core-engine/core_engine/scheduler.py`: canonical `constraint_state.session_time_budget_minutes` now flows through plan-generation runtime into generated-week scheduling, where low time budgets deterministically cap per-session exercise count without introducing new request-surface heuristics.
- `packages/core-engine/tests/test_generation.py`, `packages/core-engine/tests/test_scheduler.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine and API regressions passed for low-time session budgeting from persisted profile state.

Evidence (2026-03-10, generated-week exercise recovery pressure)
- `packages/core-engine/core_engine/scheduler.py`: generated-week now derives bounded exercise-level recovery pressure from persisted `progression_state_per_exercise`, using `fatigue_score`, `last_progression_action`, and under-target streaks to reduce planned load/sets and elevate substitution pressure without inventing new runtime inputs.
- `packages/core-engine/tests/test_scheduler.py`, `packages/core-engine/tests/test_generation.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine and API regressions passed after the new exercise-recovery-pressure path landed.

Evidence (2026-03-10, workout facade cleanup)
- `packages/core-engine/core_engine/intelligence.py`: workout helper compatibility entrypoints now preserve the legacy public surface while delegating to `decision_workout_session.py`, including session-state persistence/upsert helpers and workout-today/summary lookup runtimes.
- `packages/core-engine/tests/test_decision_workout_session.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_workout_logset_feedback.py` plus related workout API suites: focused owner-module, compatibility-wrapper, and API regressions passed after the wrapper cleanup.

Evidence (2026-03-10, SFR now affects generated week output)
- `packages/core-engine/core_engine/generation.py`: week-generation runtime now derives an SFR snapshot from canonical readiness/fatigue/adherence inputs and carries it through `prepare_generate_week_plan_runtime_inputs`.
- `packages/core-engine/core_engine/scheduler.py`: generated-week mesocycle logic now triggers `early_sfr_recovery` deloads when SFR shows high deload pressure with low recoverability, and planned exercises now emit structured `substitution_pressure` / `substitution_guidance`.
- `packages/core-engine/tests/test_generation.py`, `packages/core-engine/tests/test_scheduler.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine/API regressions now verify generation-time SFR tracing, recovery deload activation, and generated exercise substitution-pressure shaping.

Evidence (2026-03-10, generated-week repeat-failure substitution)
- `apps/api/app/routers/plan.py`, `packages/core-engine/core_engine/user_state.py`, and `packages/core-engine/core_engine/generation.py`: generate-week canonical runtime assembly now fans persisted `ExerciseState` rows into `build_plan_decision_training_state`, preserves canonical `progression_state_per_exercise`, and carries it through scheduler-runtime shaping.
- `packages/core-engine/core_engine/scheduler.py`: planned exercise assembly now applies `resolve_repeat_failure_substitution` during week generation, preserves `primary_exercise_id`, and emits structured `repeat_failure_substitution` payloads when the under-target threshold is met.
- `packages/core-engine/core_engine/rules_runtime.py`: substitution runtime now keeps the default repeat-failure threshold (`3`) even without a linked rule set, matching the documented fallback doctrine.
- `packages/core-engine/tests/test_scheduler.py`, `packages/core-engine/tests/test_rules_runtime.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine/API regressions now verify generated-week repeat-failure auto-substitution and the shared fallback threshold.

Evidence (2026-03-10, adaptive gold runtime loader support)
- `apps/api/app/program_loader.py`: runtime template loading now includes `programs/gold/*.json`, adapts `AdaptiveGoldProgramTemplate` payloads into the existing `CanonicalProgramTemplate` contract, and falls back to `docs/rules/gold/*.rules.json` when canonical rules do not contain the requested program scope.
- `apps/api/tests/test_program_loader.py`: focused loader regressions now verify that `adaptive_full_body_gold_v0_1` is loadable as a runtime template and resolves its matching gold rule set.
- `apps/api/tests/test_program_catalog_and_selection.py`: focused API regressions now verify that the adaptive gold sample appears in `/plan/programs` and can drive `POST /plan/generate-week` as a first-class runtime program.

Evidence (2026-03-10, first adaptive gold end-to-end runtime scenario)
- `apps/api/tests/test_program_catalog_and_selection.py`: the adaptive gold sample now has a real persisted runtime scenario covering `POST /plan/generate-week` -> `POST /workout/{workout_id}/log-set` -> `POST /weekly-review` -> next `POST /plan/generate-week`, proving the program remains selected across the loop and that the second generated week carries the saved weekly-review adaptive overlay on the gold path.

Evidence (2026-03-10, adaptive gold repeat-failure substitution path)
- `apps/api/app/program_loader.py`: adaptive-gold runtime template adaptation now hydrates canonical exercise names, movement patterns, primary muscles, and valid substitution metadata from `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` instead of dropping that knowledge at the loader boundary.
- `apps/api/app/template_schema.py` and `packages/core-engine/core_engine/scheduler.py`: canonical exercises now preserve optional substitution metadata so generated-week auto-substitution can update substituted exercise id/name/movement/equipment payloads instead of only swapping the display label.
- `apps/api/tests/test_program_loader.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused loader/API regressions now verify that the adaptive gold runtime template surfaces `Incline Dumbbell Press` as the valid bench substitute and that generated-week actually auto-substitutes on the gold path when failed-exposure state reaches the doctrine threshold.

Evidence (2026-03-10, expanded adaptive gold runtime proof)
- `apps/api/tests/test_program_catalog_and_selection.py`: the adaptive-gold API path now also proves canonical-readiness-driven `early_sfr_recovery` deload behavior and persisted weekly-review overlay application on the next generated week, in addition to the already-covered base generate-week, log-set, weekly-review, and repeat-failure substitution scenarios.
- The gold-path suite now covers five focused runtime proofs on `adaptive_full_body_gold_v0_1`: first generation, persisted log-set + weekly review loop, repeat-failure substitution, canonical readiness recovery deload, and saved adaptive-review application.

Evidence (2026-03-10, adaptive gold workout continuity)
- `apps/api/tests/test_workout_session_state.py`: focused workout regressions now verify that `GET /workout/today` reflects the same adaptive-gold repeat-failure substitution selected during generated-week planning and that `POST /workout/{workout_id}/log-set` preserves substitution guidance continuity into the subsequent `GET /workout/today` payload on the gold program.
- `apps/api/tests/test_workout_resume.py` and `apps/api/tests/test_workout_logset_feedback.py`: adjacent workout resume/log-set suites remain green after the new gold-path continuity coverage, confirming no regression in the broader workout runtime contract.

Evidence (2026-03-10, adaptive gold second-exercise doctrine coverage)
- `apps/api/tests/test_program_catalog_and_selection.py`: adaptive-gold generated-week substitution proof now covers both current exercise families in the sample, including the aliased `row_chest_supported` -> `Row Machine Chest Supported` repeat-failure path.
- `packages/core-engine/core_engine/scheduler.py`: substitution metadata fallback now preserves original movement/equipment/muscle metadata when the substitute entry is only partially described, instead of overwriting valid source metadata with explicit `None` values.
- `apps/api/tests/test_workout_session_state.py`: workout-side substitution continuity is now also proven for the second adaptive-gold exercise family, not only the bench press path.

Evidence (2026-03-10, adaptive gold sample expansion to third exercise family)
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the authored adaptive-gold sample now includes a third onboarding-backed vertical-pull slot (`lat_pulldown_wide`) while keeping the same single-session runtime shape.
- `apps/api/tests/test_program_loader.py`: loader regressions now verify that the adaptive-gold runtime template exposes the third vertical-pull exercise and its canonical substitute (`Neutral Grip Assisted Pull-Up`).
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold doctrine proof now covers generated-week and workout-side continuity for the third exercise family as well, including repeat-failure/equipment-driven substitution to `pullup_assisted_neutral`.

Evidence (2026-03-10, adaptive gold sample expansion to fourth exercise family)
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the authored adaptive-gold sample now includes a fourth lower-body slot (`hack_squat`) while preserving the same single-session loader/runtime contract.
- `apps/api/tests/test_program_loader.py`: loader regressions now verify that the adaptive-gold runtime template exposes the lower-body slot and its canonical fallback substitute label (`Split Squat Db`).
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold doctrine proof now covers generated-week and workout continuity for the fourth exercise family too, including repeat-failure substitution from `hack_squat` to `split_squat_db`.

Evidence (2026-03-10, adaptive gold sample expansion to core/ab work)
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the authored adaptive-gold sample now includes a fifth core slot (`cable_crunch`) while preserving the same single-session loader/runtime contract.
- `apps/api/tests/test_program_loader.py`: loader regressions now verify that the adaptive-gold runtime template exposes the new core/ab slot with canonical runtime fields.
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold runtime proof now verifies that generated-week and `GET /workout/today` both retain the core slot when cable equipment is available.

Evidence (2026-03-10, adaptive gold sample expansion to hinge/posterior-chain work)
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the authored adaptive-gold sample now includes a sixth posterior-chain slot (`romanian_deadlift`) while preserving the same single-session loader/runtime contract.
- `apps/api/tests/test_program_loader.py`: loader regressions now verify that the adaptive-gold runtime template exposes the hinge slot with canonical movement metadata and substitute label (`Leg Curl Seated`).
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold runtime proof now verifies that generated-week and `GET /workout/today` both retain the hinge slot when barbell/dumbbell equipment is available.

Evidence (2026-03-10, adaptive gold sample expansion to accessory + weak-point work)
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the authored adaptive-gold sample now includes two additional onboarding-backed weak-area/accessory slots: `weak_chest_cable_fly` and `weak_ham_leg_curl`.
- `apps/api/tests/test_program_loader.py`: loader regressions now verify that the adaptive-gold runtime template exposes both weak-point slots with canonical movement metadata and valid substitute labels.
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold runtime proof now verifies that generated-week and `GET /workout/today` both retain the chest and hamstring weak-point slots when cable/machine equipment is available.

Evidence (2026-03-10, canonical arm-isolation gap closed on adaptive gold)
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`: the gold onboarding exercise library now includes canonical entries for `dumbbell_curl_incline` and `triceps_pushdown_rope`, closing the prior arm-isolation metadata gap.
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the adaptive-gold sample now includes both arm-isolation slots inside a richer authored week rather than serving as evidence for the old compressed three-day shape.
- `apps/api/app/program_loader.py`, `apps/api/app/adaptive_schema.py`, and `apps/api/app/template_schema.py`: adaptive-gold runtime loading now preserves `day_role` as well as `slot_role`, and keeps the authored five-day structure through the runtime boundary while still exposing deterministic `days_supported` compression targets.
- `packages/core-engine/core_engine/scheduler.py` and `packages/core-engine/tests/test_scheduler.py`: generated-week compression now starts from the authored five-day source, preserves the dedicated `weak_point_arms` day when possible, and keeps all primary compound patterns alive by merging dropped-day work into retained sessions instead of trimming only by authored order.
- `apps/api/tests/test_program_catalog_and_selection.py` and `apps/api/tests/test_workout_session_state.py`: adaptive-gold API/workout proof now verifies the authored five-day runtime shape plus bounded compression behavior, replacing the earlier three-day proof as the fidelity baseline.
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the adaptive-gold sample now also includes a distinct authored week 2, so the gold baseline is no longer a single repeated week.
- `apps/api/app/template_schema.py` and `apps/api/app/program_loader.py`: the canonical adaptive-gold runtime template now preserves `authored_weeks`, keeping week variants available to generation instead of collapsing everything to week 1.
- `packages/core-engine/core_engine/scheduler.py`: generate-week now selects authored week variants from `prior_generated_weeks` before day compression and time-budget capping, so later authored weeks still honor the same weak-point preservation rules.
- `apps/api/tests/test_program_loader.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused regressions now prove authored week preservation, second-week selection, and week-2 weak-point preservation under constrained time/frequency.
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the adaptive-gold sample now also includes an authored week 3 progression step and an explicit authored week-4 deload.
- `apps/api/app/adaptive_schema.py`, `apps/api/app/template_schema.py`, and `apps/api/app/program_loader.py`: adaptive-gold runtime loading now preserves optional `week_role` so authored deload doctrine survives the loader boundary instead of being inferred downstream.
- `packages/core-engine/core_engine/scheduler.py` and `packages/core-engine/tests/test_scheduler.py`: mesocycle output now records `authored_week_index` and `authored_week_role`, and authored deload weeks now activate `deload.active` with `deload_reason == \"authored_deload\"` before any frequency/time compression logic runs.
- `apps/api/tests/test_program_catalog_and_selection.py`: focused regressions now prove third-week selection and authored week-4 deload selection on the adaptive-gold API path.
- `programs/gold/adaptive_full_body_gold_v0_1.json`: the adaptive-gold sample now extends to a 10-week authored mesocycle aligned to the onboarding package sequence `build_a / build_b / build_a / build_b / build_a / deload / intens_a / intens_b / intens_a / intens_b`, instead of stopping at an early 4-week proof slice.
- `apps/api/tests/test_program_loader.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused regressions now prove the full later-week contract, including week-2 Build-B selection (`6-9`), week-6 authored deload selection, and weeks 8 and 10 intensification selection (`4-6`) on the adaptive-gold API path.
- `packages/core-engine/core_engine/scheduler.py` and `packages/core-engine/tests/test_scheduler.py`: when an authored deload overlaps the generic cadence, the mesocycle trace now prefers `authored_deload` as the primary reason instead of mixing it with the generic scheduled reason.
- `docs/plans/2026-03-11-user-testing-rollout-plan.md`: user testing now has an explicit rollout plan covering internal dogfooding and closed beta on desktop and mobile browsers, so release readiness is no longer implicit.
- `packages/core-engine/core_engine/scheduler.py`: post-authored-sequence behavior is now explicit. When `prior_generated_weeks` exceeds the final authored week, generated-week holds the last authored week as the deterministic fallback while surfacing `authored_sequence_complete`, `phase_transition_pending`, `phase_transition_reason == "authored_sequence_complete"`, and `post_authored_behavior == "hold_last_authored_week"` in `mesocycle`.
- `packages/core-engine/tests/test_scheduler.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine/API regressions now prove the post-week-10 contract on the adaptive-gold path instead of leaving that edge case implicit.
- `packages/core-engine/core_engine/user_state.py` and `apps/api/app/adaptive_schema.py`: canonical training state now preserves that same post-authored-sequence context in `generation_state.latest_mesocycle`, so downstream decision families no longer need to rediscover it from raw latest-plan payloads.
- `packages/core-engine/core_engine/decision_progression.py` and `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview phase transition now surfaces authored-sequence completion as first-class coaching guidance with `transition_pending`, `recommended_action == "rotate_program"`, and `post_authored_behavior == "hold_last_authored_week"` instead of burying the signal in scheduler output only.
- `packages/core-engine/core_engine/decision_program_recommendation.py`: explicit authored-sequence completion now outranks day-adaptation upgrades when recommending the next template, so the app can recommend rotating off the completed adaptive-gold block instead of pretending it is still mid-mesocycle.
- `packages/core-engine/tests/test_decision_progression.py`, `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_decision_program_recommendation.py`, `packages/core-engine/tests/test_user_state.py`, `apps/api/tests/test_plan_intelligence_api.py`, `apps/api/tests/test_program_recommendation_and_switch.py`, and `apps/api/tests/test_profile_training_state.py`: focused regressions now prove that post-week-10 transition state survives the full path from latest plan -> canonical state -> coach preview -> program recommendation -> API payloads.
- `apps/api/tests/test_program_loader.py`, `apps/api/tests/test_program_catalog_and_selection.py`, and `apps/api/tests/test_workout_session_state.py`: focused loader/generate-week/workout regressions now verify that the biceps and triceps isolation slots survive the runtime path with canonical names, movement patterns, and equipment tags.

Evidence (2026-03-11, Phase 1 fidelity-first five-day authored runtime)
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` and `programs/gold/adaptive_full_body_gold_v0_1.json`: the adaptive-gold path now starts from a five-day authored source with explicit `day_role` values for `Full Body #1-#4` and `Arms & Weak Points` instead of the older compressed three-day surrogate.
- `apps/api/app/program_loader.py`, `apps/api/app/adaptive_schema.py`, and `apps/api/app/template_schema.py`: loader/schema contracts now preserve that richer authored day metadata through the runtime template boundary.
- `packages/core-engine/core_engine/scheduler.py` and `packages/core-engine/tests/test_scheduler.py`: bounded frequency compression now preserves the weak-point day and all primary compound patterns when compressing from five authored days to three by merging dropped-day work into retained anchor sessions.
- `apps/api/tests/test_program_loader.py`, `apps/api/tests/test_program_catalog_and_selection.py`, and `apps/api/tests/test_workout_session_state.py`: focused loader/API/workout regressions now validate the authored five-day runtime shape and the new compression behavior end to end.

Evidence (2026-03-11, source-truth import pipeline repaired for real Phase 1 workbook)
- `importers/xlsx_to_program.py`: workbook header detection now correctly selects the real `Exercise / Working Sets / Reps` header row instead of top-of-sheet note blocks; Excel `m-d` serial cells are converted back into readable warm-up strings; and superset prefixes are stripped before exercise ids are slugged.
- `apps/api/tests/test_xlsx_to_onboarding_v2.py` and `apps/api/tests/test_xlsx_to_program_v2.py`: source-backed regressions now prove the real workbook imports as 10 weeks / 5 authored days with the actual Phase 1 day names and first-day exercise ids.
- `importers/xlsx_to_program.py`: key workbook exercise metadata is now corrected at the source boundary through improved inference/overrides, including `leg_press -> squat`, `seated_db_shoulder_press -> vertical_press`, `triceps_pressdown_bar -> triceps_extension`, and `bayesian_cable_curl -> curl`.
- `apps/api/app/program_loader.py` and `apps/api/tests/test_program_loader.py`: the adaptive-gold loader can now flatten all authored weeks from a source-backed multi-phase adaptive bundle instead of dropping everything after the first phase.

Immediate next target (2026-03-11)
- Migrate the live gold onboarding/runtime artifacts from the repaired workbook pipeline into the actual runtime path.
- Preserve already-proven runtime semantics during that migration:
  - `day_role`
  - `slot_role`
  - weak-point preservation under compression
  - authored sequence / transition state
  - adaptive-gold API/workout continuity

Evidence (2026-03-10, coach-preview specialization/media ownership extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: specialization-adjustment and program-media/warmup summarization helpers now live in the coach-preview decision-family module instead of `intelligence.py`.
- `packages/core-engine/core_engine/intelligence.py`: those specialization/media entrypoints now delegate through thin compatibility wrappers.
- `packages/core-engine/core_engine/__init__.py`: package exports now source those helpers from the decision-family module.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused engine/wrapper/API regressions now verify the new ownership boundary.

Evidence (2026-03-10, workout summary and exercise-state ownership extraction)
- `packages/core-engine/core_engine/decision_workout_session.py`: now owns workout performance summary, log-set request/runtime shaping, session-state defaults/persistence helpers, workout-today plan/log/progression runtime helpers, and repeat-failure substitution payload shaping used by the workout route-runtime family.
- `packages/core-engine/core_engine/__init__.py`: package exports for those workout helper families now source from `decision_workout_session.py`.
- `packages/core-engine/tests/test_decision_workout_session.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_workout_logset_feedback.py`, `tests/test_workout_session_state.py`, `tests/test_workout_summary.py`, `tests/test_workout_resume.py`, `tests/test_workout_progress.py`: focused engine/wrapper/API regressions now verify the moved workout ownership path.

### Task 0.1 - Ingestion-Centered Architecture Audit
- Identify code to keep/isolate/deprecate/delete.
- Deliver explicit list with file paths and rationale.
- Status: DONE (`docs/redesign/Architecture_Audit_Matrix.md`)

### Task 0.2 - Canonical Schema Finalization
- Finalize typed contracts for templates/catalog/rules/user state.
- Add schema validation tests.
- Status: STARTED (`apps/api/app/adaptive_schema.py`, `apps/api/tests/test_adaptive_gold_schema_contract.py`)

Evidence (2026-03-07)
- `apps/api/app/adaptive_schema.py`: added cross-field validators for onboarding package program-id alignment and blueprint week-template sequence coverage.
- `apps/api/app/adaptive_schema.py`: added uniqueness validators for `week_template.day_id`, `day.slot_id`, and `day.order_index` values.
- `apps/api/tests/test_program_onboarding_contract.py`: added negative-path contract tests for mismatched program IDs, unknown week templates in `week_sequence`, and duplicate slot ordering.

Evidence (2026-03-08)
- `apps/api/app/adaptive_schema.py`: adaptive gold template schema now enforces literal `work`/`top`/`backoff` set types, optional warmup `rest_seconds`, unique adaptive phase IDs, unique week indexes per phase, unique day IDs per week, unique slot IDs/order indices per day, and non-empty unique gold rule `program_scope`.
- `apps/api/app/adaptive_schema.py`: canonical user-state contracts now include `UserProgramState`, `ExercisePerformanceEntry`, `ProgressionStateEntry`, `FatigueState`, `AdherenceState`, `StallState`, and `UserTrainingState`, with uniqueness validation for `progression_state_per_exercise`.
- `apps/api/tests/test_adaptive_gold_schema_contract.py`: added negative-path contract tests for duplicate adaptive week indexes, duplicate slot order indices, invalid work-set types, and empty/duplicate gold rule `program_scope`.
- `apps/api/tests/test_user_training_state_schema_contract.py`: direct contract coverage for valid user-state payloads, duplicate progression-state rejection, and invalid nested range rejection.
- `apps/api/tests/test_xlsx_to_program_v2.py` and `apps/api/tests/test_pdf_doctrine_rules_v1.py`: importer/rule-distillation regression coverage remains green against the tightened adaptive schema contracts.
- `scripts/mini_validate.sh`: full gate remained green after the user-state contract addition (`121` API tests passed, `33` web tests passed, Next.js production build succeeded).

### Task 0.3 - Gold Sample Pair
- Build one manually validated gold program + matching rule set.
- Status: STARTED (`programs/gold/*`, `docs/rules/gold/*`)

### Task 0.4 - Onboarding Package Domain Store
- Maintain one onboarding package per runtime template id.
- Validate package schema and loader stability.
- Status: STARTED

Evidence (2026-03-06)
- `apps/api/app/program_loader.py`: onboarding package loaders + runtime catalog filter for canonical templates.
- `apps/api/tests/test_program_onboarding_contract.py`: package contract and loader tests.

## Priority 1 - Importer and Rules

### Task 1.1 - Excel Importer v2
- Preserve phase/week/day/slot fidelity.
- Preserve warmups/work sets/videos/notes.
- Emit ambiguity diagnostics.

Evidence (2026-03-07)
- `importers/xlsx_to_program.py`: transitional workbook importer now emits explicit `import_diagnostics` metadata for missing headers, defaulted session grouping, skipped structural labels, and missing numeric prescriptions.
- `importers/xlsx_to_program.py`: imported templates now retain `source_workbook` provenance in emitted JSON.
- `importers/xlsx_to_program.py`: repeated identical session labels now remain grouped in the same session instead of being flushed into separate sessions row-by-row.
- `importers/structured_program_builder.py`: shared structured-builder helpers now convert parsed workbook sessions into canonical blueprint days/slots, exercise-library entries, and adaptive gold weeks.
- `importers/xlsx_to_program.py`: workbook parsing now extracts authored phase/week markers and richer slot semantics including `set_type`, `rpe_target`, `load_target`, `warmup_sets`, and parsed rest metadata.
- `importers/structured_program_builder.py`: blueprint and adaptive-gold emitters now preserve authored multi-week/multi-phase structure when the workbook contains more than one authored week, while keeping single-week repetition as an explicit fallback.
- `importers/xlsx_to_program_v2.py`: new build-time structured exporter emits schema-validated adaptive gold program templates plus sidecar import reports with explicit diagnostics.
- `importers/xlsx_to_onboarding_v2.py`: onboarding package builder now uses the shared structured workbook collector instead of the stale parser shape.
- `apps/api/tests/test_xlsx_to_program_sanitization.py`: coverage for structural-row sanitization plus emitted diagnostics and defaulted-session warnings.
- `apps/api/tests/test_xlsx_to_program_v2.py`: coverage that the new structured exporter emits a valid adaptive gold template and diagnostics report, and preserves authored phase/week boundaries plus `top`/`backoff`/`load_target`/`rpe_target` semantics.
- `apps/api/tests/test_xlsx_to_onboarding_v2.py`: regression coverage that onboarding package generation still works against the current parser result shape.
- `apps/api/tests/test_xlsx_to_program_video_mapping.py`: coverage that workbook video links still map deterministically to `video.youtube_url` only for YouTube URLs.

### Task 1.2 - PDF Rule Distillation v1
- Convert doctrine to typed deterministic rules.
- Link rules to source references.

Evidence (2026-03-07)
- `apps/api/app/adaptive_schema.py`: adaptive rule-set schema now supports provenance-backed `source_sections` metadata and richer optional work-set load targets.
- `importers/pdf_doctrine_rules_v1.py`: new build-time distiller resolves normalized guide docs from provenance, extracts deterministic rule hints from doctrine text, and emits schema-validated adaptive rule JSON with source excerpts.
- `docs/rules/canonical/pure_bodybuilding_phase_1_full_body.rules.json`: first canonical rules artifact emitted from the normalized guide corpus for the Phase 1 full-body program.
- `apps/api/tests/test_pdf_doctrine_rules_v1.py`: regression coverage for grounded doctrine extraction and JSON emission.

## Priority 2 - Decision Engine Gold Flow

### Task 2.1 - Deterministic Adaptation Core
- Workout generation from template + rules + state.
- Post-session evaluation and next-session adaptation.
- Status: STARTED

Evidence (2026-03-06)
- `packages/core-engine/core_engine/onboarding_adaptation.py`: deterministic adaptation decisions (`preserve/combine/rotate/reduce`).
- `apps/api/app/routers/plan.py`: `POST /plan/adaptation/preview` wired to onboarding package + user weak-area overlay.
- `apps/api/tests/test_program_frequency_adaptation_api.py`: API coverage for deterministic adaptation preview.
- `packages/core-engine/tests/test_onboarding_adaptation.py`: core adaptation tests for target day changes.

Evidence (2026-03-07)
- `packages/core-engine/core_engine/intelligence.py`: workout sovereignty now includes `resolve_workout_session_state_update`, `build_workout_session_state_defaults`, `prepare_workout_session_state_persistence_payload`, `build_workout_progress_payload`, and `build_workout_today_payload` for live session-state reduction and today/progress response shaping.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_today_session_selection` now owns the choose-resume/today/fallback policy for `GET /workout/today`.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_plan_reference` now owns stored workout-plan traversal for planned session, planned exercise, and program-id lookup.
- `packages/core-engine/core_engine/intelligence.py`: `build_program_recommendation_payload` and `build_program_switch_payload` now own deterministic profile recommendation/switch payload and decision-trace assembly.
- `packages/core-engine/core_engine/intelligence.py`: `build_weekly_review_performance_summary`, `build_weekly_review_decision_payload`, and `build_weekly_review_submit_payload` now own weekly review summary preparation, submit decision packaging, and response shaping.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_completion_per_exercise` now owns highest-set completion aggregation for logged workout sets.
- `packages/core-engine/core_engine/intelligence.py`: `group_workout_logs_by_exercise`, `build_workout_summary_payload`, and `build_workout_performance_summary` now own workout summary log bucketing, per-exercise runtime preparation, and final response assembly.
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_today_state_payloads` now owns persisted session-state merging and live recommendation hydration for `GET /workout/today`.
- `packages/core-engine/core_engine/generation.py`: guide catalog/day/exercise payload builders now own plan guide display-name and response shaping.
- `packages/core-engine/core_engine/intelligence.py`: `build_coach_preview_payloads` and `build_frequency_adaptation_apply_payload` now own the remaining deterministic response/persistence shaping for `apps/api/app/routers/plan.py` coach-preview and adaptation-apply flows.
- `packages/core-engine/core_engine/intelligence.py`: `prepare_phase_apply_runtime` and `prepare_specialization_apply_runtime` now own `apps/api/app/routers/plan.py` recommendation-payload normalization, fallback next-phase handling, and applied-record field assembly for coach apply flows.
- `packages/core-engine/core_engine/intelligence.py`: `build_generated_week_plan_payload` now owns `apps/api/app/routers/plan.py` final returned-plan assembly for `POST /plan/generate-week`, including template/runtime trace attachment, weekly-review overlays, and active adaptation runtime application.
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_log_set_payload` now owns `apps/api/app/routers/workout.py` deterministic log-set response assembly, including planned-vs-actual feedback payload wrapping and live recommendation embedding.
- `packages/core-engine/core_engine/generation.py`: `prepare_generation_template_runtime` now owns `apps/api/app/routers/plan.py` template loading/selection orchestration for coach-preview and generate-week around `resolve_generation_template_choice`.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_latest_logged_workout_resume_state` now owns `apps/api/app/routers/workout.py` latest logged-session and incomplete-session derivation for `GET /workout/today` resume eligibility.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set`, `GET /workout/{workout_id}/progress`, `GET /workout/{workout_id}/summary`, and `GET /workout/today` now keep DB reads and resume-eligibility queries in-router while delegating deterministic selection, session-state payload prep, and response shaping to core-engine helpers.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now keeps only the workout-log/session-state SQL reads in-router while delegating resume-state derivation, session selection, completed-set aggregation, and response shaping to core-engine helpers.
- `apps/api/app/routers/profile.py`: `GET /profile/program-recommendation` and `POST /profile/program-switch` now keep only latest-user-state SQL reads in-router while delegating candidate resolution and deterministic program-selection runtime prep to `prepare_program_recommendation_runtime`; switch apply-vs-preflight gating and compatibility validation now route through `prepare_program_switch_runtime`.
- `apps/api/app/routers/profile.py`: `POST /weekly-review` now keeps summary SQL reads and persistence in-router while delegating decision packaging and submit-response shaping to core-engine helpers.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` and `POST /plan/generate-week` now keep HTTP error translation, SQL reads, and persistence in-router while delegating template loading/selection orchestration to `prepare_generation_template_runtime`.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` now centralizes its canonical training-state SQL fan-in plus `resolve_week_generation_runtime_inputs` wiring through `_prepare_plan_generation_runtime`, reducing route-body drift while keeping SQL and persistence in-router.
- `apps/api/app/routers/workout.py`: `GET /workout/today` and `GET /workout/{workout_id}/progress` now keep log queries in-router while delegating completed-set aggregation to a core-engine helper.
- `apps/api/app/routers/workout.py`: `GET /workout/{workout_id}/summary` now keeps planned-session, workout-log, and bulk progression-state SQL reads in-router while delegating per-exercise summary preparation and final summary-response shaping to core-engine helpers.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now keeps session-state queries in-router while delegating persisted state merging and live recommendation shaping to a core-engine helper.
- `apps/api/app/routers/plan.py`: guide catalog/day/exercise endpoints now keep template loading and error handling in-router while delegating payload shaping to core-engine generation helpers.
- `packages/core-engine/tests/test_intelligence.py`: direct regression coverage for workout session-state reduction, today-session selection, stored-plan lookup, and today/progress payload shaping.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_recommendation_and_switch.py`: regression coverage for extracted program-recommendation runtime preparation plus program-switch runtime preparation, including shared candidate-resolution traces, incompatible-target rejection, and confirmed-change persistence gating.
- `packages/core-engine/tests/test_generation.py`, `apps/api/tests/test_program_catalog_and_selection.py`, and `apps/api/tests/test_plan_intelligence_api.py`: regression coverage for extracted template loading/selection orchestration used by coach-preview and generate-week.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_resume.py`: regression coverage for extracted workout resume-state derivation plus the unchanged resume-vs-today observable API behavior.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: regression coverage for weekly review summary preparation plus submit payload extraction.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_progress.py`, and `apps/api/tests/test_workout_resume.py`: regression coverage for completed-set aggregation extraction.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_summary.py`: regression coverage for workout summary log-grouping and response-shaping extraction.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_resume.py`, and `apps/api/tests/test_workout_session_state.py`: regression coverage for workout-today session-state merge extraction.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_plan_guides_api.py`: regression coverage for plan guide payload extraction.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_plan_intelligence_api.py`, and `apps/api/tests/test_program_frequency_adaptation_api.py`: regression coverage for plan coach-preview and frequency-adaptation response payload extraction.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_plan_intelligence_api.py`: regression coverage for extracted coach apply runtime preparation, including fallback next-phase handling and missing-specialization error behavior.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_program_catalog_and_selection.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`, and `apps/api/tests/test_weekly_review.py`: regression coverage for the `POST /plan/generate-week` finalizer extraction.
- `apps/api/tests/test_program_catalog_and_selection.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`, and `apps/api/tests/test_weekly_review.py`: focused API regression coverage remained green after the `plan_generate_week` training-state/runtime-prep helper extraction.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_logset_feedback.py`, and `apps/api/tests/test_workout_session_state.py`: regression coverage for the workout log-set response payload extraction.
- `apps/web/app/page.tsx` and `apps/web/tests/home.dashboard.test.tsx`: home dashboard now surfaces coach-priority actions, session blueprint prescriptions, block context, and momentum summaries from existing runtime APIs.
- `apps/web/app/checkin/page.tsx` and `apps/web/tests/checkin.review.test.tsx`: weekly review now surfaces a command-center summary, nutrition snapshot, fault severity audit, and humanized adaptive output from existing review APIs.
- `apps/web/app/week/page.tsx` and `apps/web/tests/week.program.test.tsx`: week plan now surfaces a planning cockpit with command-deck, mesocycle, coverage, session-blueprint, adaptive-review, and frequency-adaptation summaries while keeping `/plan/generate-week` override and Sunday-review guard behavior covered.
- `apps/web/app/today/page.tsx` and `apps/web/tests/today.runner.test.tsx`, `apps/web/tests/today.logset.test.tsx`, `apps/web/tests/today.substitution.test.tsx`: today now surfaces pre-session intent and a between-set coach card tied to workout/progress/live-guidance payloads, while preserving runner, log-set, and substitution flows.
- `apps/web/app/history/page.tsx` and `apps/web/tests/history.calendar.test.tsx`: history now surfaces a progression brief plus strength/bodyweight/coach-queue summaries in addition to the existing calendar drill-down and same-weekday comparison flows.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_weekly_review_window` and `build_weekly_review_status_payload` now own weekly review date-window and status-resolution logic.
- `apps/api/app/routers/profile.py`: weekly review status and default review-week resolution now keep DB reads/persistence in-router while delegating deterministic date-window, previous-week summary preparation, and response-status shaping to core-engine helpers.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: regression coverage for weekly review window/status extraction.
- `apps/api/tests/test_workout_logset_feedback.py`, `apps/api/tests/test_workout_progress.py`, and `apps/api/tests/test_workout_resume.py`: API coverage for the preserved workout contracts after the extraction.

Evidence (2026-03-08)
- `packages/core-engine/core_engine/rules_runtime.py`: first dedicated rules-runtime module now resolves canonical starting-load runtime and normalized progression rule runtime from typed rule-set payloads.
- `packages/core-engine/core_engine/progression.py`: progression rule percent/exposure thresholds now read through `resolve_progression_rule_runtime` instead of ad hoc inline parsing.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now resolves first-exposure starting load through `resolve_starting_load`, seeds new `ExerciseState` records from estimated-1RM fallback when present, and surfaces an optional `starting_load_decision_trace` in the response.
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_performance_summary` now owns workout-summary runtime preparation from raw workout-log rows plus bulk progression-state rows, including per-exercise next-load selection before final session guidance is derived.
- `apps/api/app/routers/workout.py`: `GET /workout/{workout_id}/summary` now performs a single bulk `ExerciseState` query for the session and delegates the remaining summary normalization/aggregation to `build_workout_performance_summary`.
- `packages/core-engine/core_engine/intelligence.py`: `build_repeat_failure_substitution_payload` now owns repeat-failure substitution payload shaping, and `build_workout_today_session_state_payloads` now prepares persisted workout-today session-state rows plus substitution guidance before final hydration.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` and `GET /workout/today` now delegate repeat-failure substitution payload preparation to core-engine instead of shaping that payload inline in the router.
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_log_set_plan_context` now owns planned-exercise normalization for `POST /workout/{workout_id}/log-set`, including rep-range coercion, planned-set fallback, and planned-weight fallback.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now delegates planned exercise context shaping to `resolve_workout_log_set_plan_context` before progression, starting-load, and feedback interpreters run.
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_session_state_defaults` and `prepare_workout_session_state_persistence_payload` now own default session-state seeding plus persistable state-payload preparation around `resolve_workout_session_state_update`.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now keeps only the `WorkoutSessionState` ORM fetch/create/add wrapper while delegating deterministic default-state construction and persisted field payload preparation to core-engine.
- `packages/core-engine/tests/test_rules_runtime.py` and `apps/api/tests/test_workout_logset_feedback.py`: direct engine coverage plus end-to-end API coverage for the rules-runtime starting-load path.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_summary.py`: focused regression coverage for workout-summary runtime preparation with generic row normalization and preserved API contract.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_session_state.py`: focused regression coverage for extracted repeat-failure substitution payload shaping and workout-today session-state preparation.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_logset_feedback.py`: focused regression coverage for extracted log-set planned-exercise context normalization.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_session_state.py`: focused regression coverage for extracted workout session-state default seeding and persistable payload preparation.
- `scripts/mini_validate.sh`: full gate remained green after the rules-runtime slice (`122` API tests passed, `33` web tests passed, Next.js production build succeeded).
- `packages/core-engine/core_engine/rules_runtime.py`: fatigue RPE threshold extraction, intro-week protection extraction, adaptive rule runtime normalization, and early-deload signal evaluation now live in the rules-runtime layer rather than `intelligence.py`.
- `packages/core-engine/core_engine/intelligence.py`: `recommend_progression_action` and `recommend_phase_transition` now consume `resolve_adaptive_rule_runtime` and `evaluate_deload_signal` for rule-derived fatigue and deload behavior.
- `packages/core-engine/tests/test_rules_runtime.py` and `packages/core-engine/tests/test_intelligence.py`: direct coverage now includes rule-based underperformance-plus-high-fatigue deload matching and intro/scheduled-deload runtime extraction.
- `scripts/mini_validate.sh`: full gate remained green after the fatigue/deload rules-runtime extraction as well (`122` API tests passed, `33` web tests passed, Next.js production build succeeded).

Evidence (2026-03-08, substitution runtime)
- `packages/core-engine/core_engine/rules_runtime.py`: substitution rule normalization now resolves canonical equipment-mismatch strategy and repeat-failure thresholds, and `resolve_equipment_substitution` returns a structured decision trace for equipment-based swap decisions.
- `packages/core-engine/core_engine/scheduler.py`: week-generation planning now delegates equipment mismatch handling to `resolve_equipment_substitution`, preserves compatible substitution candidates, and emits `substitution_decision_trace` on generated exercises.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` now loads the selected template rule set and passes it into `generate_week_plan`, so canonical `substitution_rules` participate in planner-side exercise selection.
- `packages/core-engine/tests/test_rules_runtime.py`, `packages/core-engine/tests/test_scheduler.py`, and `apps/api/tests/test_program_catalog_and_selection.py`: direct engine and API-adjacent coverage now verifies substitution rule parsing, auto-selection of the first compatible substitute, structured substitution traces, and rule-set threading through generated-week planning.
- `scripts/mini_validate.sh`: full gate remained green after the substitution rules-runtime extraction as well (`122` API tests passed, `33` web tests passed, Next.js production build succeeded).

Evidence (2026-03-08, repeat-failure substitution runtime)
- `packages/core-engine/core_engine/progression.py`: `ExerciseState` now tracks `consecutive_under_target_exposures` and `last_progression_action`, so canonical under-target streak state survives across workout exposures instead of being inferred ad hoc.
- `packages/core-engine/core_engine/rules_runtime.py`: `resolve_repeat_failure_substitution` now evaluates canonical `substitution_rules.repeat_failure_trigger` against persisted under-target streak state and returns a structured recommendation trace for the first compatible alternative.
- `apps/api/app/models.py`, `apps/api/alembic/versions/0013_exercise_state_progression_tracking.py`, and `apps/api/app/routers/workout.py`: the workout API now persists under-target streak metadata on `ExerciseState`, emits optional `live_recommendation.substitution_recommendation` in `POST /workout/{workout_id}/log-set`, and rehydrates the same recommendation in `GET /workout/today`.
- `packages/core-engine/tests/test_progression.py`, `packages/core-engine/tests/test_rules_runtime.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_workout_session_state.py`: focused engine and API coverage now verifies streak tracking, repeat-failure recommendation resolution, live-guidance payload propagation, and today-screen rehydration.
- Focused validation stayed green after this slice: `packages/core-engine` targeted regressions passed (`79` tests) and `apps/api/tests/test_workout_session_state.py` passed (`4` tests).

Evidence (2026-03-08, canonical user training state runtime)
- `packages/core-engine/core_engine/user_state.py`: new `build_user_training_state` assembler now normalizes canonical `UserTrainingState` payloads from persisted workout plans, set logs, `ExerciseState`, soreness, check-ins, and weekly reviews, including derived session selection, fatigue, adherence, and stall summaries.
- `apps/api/app/routers/profile.py` and `apps/api/app/schemas.py`: `GET /profile/training-state` now exposes the canonical runtime-backed payload through a dedicated profile endpoint using `UserTrainingStateResponse`.
- `packages/core-engine/tests/test_user_state.py` and `apps/api/tests/test_profile_training_state.py`: focused engine and API coverage now verifies canonical payload assembly and endpoint behavior.
- Focused validation stayed green after this slice: `packages/core-engine/tests/test_user_state.py`, `apps/api/tests/test_profile_training_state.py`, and `apps/api/tests/test_workout_session_state.py` all passed.

Evidence (2026-03-08, canonical user-state consumption in plan runtime)
- `apps/api/app/routers/plan.py`: frequency adaptation preview/apply now build a minimal canonical user-state payload through `build_user_training_state` and pass it into `resolve_frequency_adaptation_request_context`, so current week and recovery context come from the canonical runtime contract instead of route-local plan/soreness parsing.
- `packages/core-engine/core_engine/generation.py`: `resolve_frequency_adaptation_request_context` now prefers canonical `user_program_state` and `fatigue_state`, and `resolve_week_generation_runtime_inputs` now prefers canonical performance history, adherence, `fatigue_state.soreness_by_muscle`, and `generation_state.prior_generated_weeks_by_program` when a `UserTrainingState` payload is supplied.
- `packages/core-engine/core_engine/user_state.py`, `apps/api/app/adaptive_schema.py`, and `apps/api/app/routers/profile.py`: canonical user state now carries `fatigue_state.soreness_by_muscle` plus `generation_state.prior_generated_weeks_by_program`, and `/profile/training-state` exposes those persisted generation-context fields.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused engine and API coverage stayed green after the shift to canonical user-state consumption.
- Focused validation after the contract expansion passed: `packages/core-engine/tests/test_user_state.py`, `packages/core-engine/tests/test_generation.py`, `apps/api/tests/test_user_training_state_schema_contract.py`, `apps/api/tests/test_profile_training_state.py`, and `apps/api/tests/test_program_frequency_adaptation_api.py`.

Evidence (2026-03-08, canonical user-state consumption in profile recommendation runtime)
- `apps/api/app/adaptive_schema.py` and `packages/core-engine/core_engine/user_state.py`: `generation_state` now also carries under-target-muscle context plus mesocycle trigger weeks from the latest generated plan.
- `packages/core-engine/core_engine/intelligence.py`: `prepare_program_recommendation_runtime` now prefers canonical `UserTrainingState` adherence plus generation-context inputs before falling back to isolated latest-checkin / latest-plan payload data, and the recommendation trace records those input sources explicitly.
- `apps/api/app/routers/profile.py`: `GET /profile/program-recommendation` and `POST /profile/program-switch` now build canonical user state and pass it into the shared recommendation runtime instead of assembling adherence context from isolated router-local reads.
- Focused validation passed for this slice: `packages/core-engine/tests/test_user_state.py`, `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_user_training_state_schema_contract.py`, `apps/api/tests/test_profile_training_state.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`.

Evidence (2026-03-08, canonical user-state consumption in coach preview)
- `packages/core-engine/core_engine/generation.py`: `build_coach_preview_context` now prefers canonical `UserTrainingState.exercise_performance_history` before falling back to raw serialized workout-log rows.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now builds canonical user state from recent logs and passes it into the preview context builder instead of serializing `WorkoutSetLog` rows inline.
- Focused validation passed for this slice: `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_plan_intelligence_api.py`.
- Broader validation passed afterward via `./scripts/mini_validate.sh` (`124` API tests, `33` web tests, and Next.js production build all green).

Evidence (2026-03-09, generate-week review overlay runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_generated_week_review_overlay` now owns weekly-review overlay normalization for generate-week payload assembly (adjustments dict coercion plus `week_start`/`reviewed_on` context shaping), with a structured decision trace.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` now keeps the weekly-review SQL read and delegates review overlay payload preparation to the new core-engine helper before calling `build_generated_week_plan_payload`.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: focused engine/API regressions passed for the extracted overlay path (`prepare_generated_week_review_overlay` and saved-review generate-week behavior).

Evidence (2026-03-09, frequency adaptation input-runtime extraction)
- `packages/core-engine/core_engine/generation.py`: `prepare_frequency_adaptation_runtime_inputs` now centralizes deterministic adaptation input shaping by reusing resolved program/week/recovery context and packaging normalized engine inputs with a structured decision trace.
- `apps/api/app/routers/plan.py`: `POST /plan/adaptation/preview` and `POST /plan/adaptation/apply` now call the shared core-engine runtime-input helper instead of duplicating adaptation input shaping in-route; SQL reads, onboarding package loading, and apply persistence remain in-router.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused engine/API regressions passed for the extracted adaptation input-runtime seam.

Evidence (2026-03-09, frequency adaptation trace propagation)
- `packages/core-engine/core_engine/intelligence.py`: `recommend_frequency_adaptation_preview` and `interpret_frequency_adaptation_apply` now accept optional runtime-input traces and embed them into their structured `decision_trace` payloads as `request_runtime_trace`.
- `apps/api/app/routers/plan.py`: adaptation preview/apply now pass the shared `prepare_frequency_adaptation_runtime_inputs` trace into those interpreters, preserving context-resolution provenance in API coaching output.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regression coverage verifies runtime-trace propagation in adaptation decision traces.

Evidence (2026-03-09, coach-preview request runtime extraction)
- `packages/core-engine/core_engine/generation.py`: `prepare_coach_preview_runtime_inputs` now centralizes coach-preview request day normalization (`from_days`, `to_days`, profile-days fallback, and `max_requested_days`) with a structured decision trace.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now uses the shared runtime-input helper before template selection and forwards that helper trace into `recommend_coach_intelligence_preview`.
- `packages/core-engine/core_engine/intelligence.py`: coach-preview decision traces now include optional `request_runtime_trace` so upstream request-shaping provenance is preserved in recommendation output.
- `packages/core-engine/tests/test_generation.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused engine/API regressions passed for coach-preview runtime extraction and trace propagation.

Evidence (2026-03-09, coach-preview template-selection trace propagation)
- `packages/core-engine/core_engine/intelligence.py`: `recommend_coach_intelligence_preview` now accepts optional `template_runtime_trace` and persists it into the structured coach-preview decision trace.
- `apps/api/app/routers/plan.py`: coach-preview now passes `prepare_generation_template_runtime` decision trace into the core-engine coach-preview interpreter, linking template selection provenance to final coaching output.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed for template-selection trace propagation in coach-preview output.

Evidence (2026-03-09, coach-preview record payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_coach_preview_recommendation_record_fields` now owns deterministic record-field shaping for persisted coach-preview recommendations.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now uses that helper when creating `CoachingRecommendation`, keeping route-level responsibilities to SQL writes/commit only.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed for persisted coach-preview payload shaping after extraction.

Evidence (2026-03-09, coach apply source-runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_coaching_apply_runtime_source` now normalizes persisted preview recommendation payload/fields for apply-phase and apply-specialization runtime prep.
- `apps/api/app/routers/plan.py`: apply-phase/apply-specialization now use that shared helper before `prepare_phase_apply_runtime` / `prepare_specialization_apply_runtime`, reducing route-local recommendation-payload coercion.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed for apply route behavior after source-runtime extraction.

Evidence (2026-03-09, coach apply interpreter and applied-record extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach apply decision interpretation and applied-record payload builders now own `interpret_coach_phase_apply_decision`, `interpret_coach_specialization_apply_decision`, `build_phase_applied_recommendation_record`, and `build_specialization_applied_recommendation_record`.
- `packages/core-engine/core_engine/intelligence.py`: stable public wrappers now delegate those decision-family internals to `decision_coach_preview.py` so router contracts remain unchanged.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused module/engine/API regressions passed for the extracted apply-decision seam.

Evidence (2026-03-09, coach apply finalization payload extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: `finalize_applied_coaching_recommendation` now owns deterministic apply-finalization payload shaping (applied recommendation ID trace injection and response payload enrichment).
- `packages/core-engine/core_engine/intelligence.py`: stable public wrapper now delegates finalization to the coach-preview decision module.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after apply-finalization extraction.

Evidence (2026-03-09, coach-preview recommendation assembly extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview recommendation assembly internals now own schedule/progression payload shaping, readiness-score fallback handling, decision-trace packaging, and `recommend_coach_intelligence_preview` orchestration.
- `packages/core-engine/core_engine/intelligence.py`: `recommend_coach_intelligence_preview` now delegates to the decision module via stable wrapper entrypoint while injecting existing decision dependencies (schedule adaptation, progression/phase/specialization interpreters, humanizers, and media/warmup summarization).
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused module/engine/API regressions passed after coach-preview assembly extraction.

Evidence (2026-03-09, coaching recommendation timeline extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: timeline rationale normalization and payload shaping now own `resolve_coaching_recommendation_rationale`, `extract_coaching_recommendation_focus_muscles`, `build_coaching_recommendation_timeline_entry`, `build_coaching_recommendation_timeline_payload`, and `normalize_coaching_recommendation_timeline_limit`.
- `packages/core-engine/core_engine/intelligence.py`: stable public wrappers now delegate timeline shaping internals to `decision_coach_preview.py` while preserving endpoint contracts.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused module/engine/API regressions passed after timeline extraction.

Evidence (2026-03-09, shared plan/profile training-state assembly extraction)
- `packages/core-engine/core_engine/user_state.py`: `build_plan_decision_training_state` now owns shared plan/profile training-state payload assembly defaults on top of canonical `build_user_training_state` (logs/checkins/reviews/prior-plans coercion with no router-local exercise-state dependency).
- `apps/api/app/routers/plan.py` and `apps/api/app/routers/profile.py`: plan generate-week/coach-preview/adaptation and profile recommendation runtime prep now reuse that helper instead of route-local training-state shaping functions.
- `packages/core-engine/tests/test_user_state.py`, `apps/api/tests/test_plan_intelligence_api.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`, `apps/api/tests/test_profile_training_state.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`: focused engine/API regressions passed after shared training-state extraction.

Evidence (2026-03-09, apply response finalization helper extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: `build_applied_coaching_recommendation_response` now owns shared apply response finalization wiring for coach apply endpoints by delegating deterministic payload/trace finalization through the decision-family module.
- `packages/core-engine/core_engine/intelligence.py`: stable wrapper now delegates apply response finalization to the decision module.
- `apps/api/app/routers/plan.py`: apply-phase and apply-specialization now call the shared helper instead of route-local finalization wiring.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after apply response helper extraction.

Evidence (2026-03-09, applied recommendation record-values extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: `build_applied_coaching_recommendation_record_values` now owns deterministic applied-record constructor payload shaping (`user_id`, empty initial recommendation payload, applied timestamp, and normalized record fields).
- `packages/core-engine/core_engine/intelligence.py`: stable wrapper now delegates applied-record constructor payload shaping to the decision module.
- `apps/api/app/routers/plan.py`: apply-phase and apply-specialization now reuse this shared helper when creating `CoachingRecommendation` applied records.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after applied-record payload extraction.

Evidence (2026-03-09, coach-preview context runtime extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: `prepare_coach_preview_decision_context` now owns deterministic coach-preview context prep by combining canonical training-state assembly and context payload defaults (`nutrition_phase`, equipment list normalization) with structured trace metadata.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now delegates training-state/context shaping to the shared helper before calling `recommend_coach_intelligence_preview`.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after coach-preview context extraction.

Evidence (2026-03-09, weekly-review submit window extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_weekly_review_submit_window` now owns weekly-review submit week-window resolution (requested week override vs runtime default window, plus previous-week derivation) with structured decision trace.
- `apps/api/app/routers/profile.py`: `POST /weekly-review` now delegates week-window shaping to the new helper before summary/decision/persistence orchestration.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: focused regressions passed for weekly-review submit behavior after extraction.

Evidence (2026-03-09, workout-today plan runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_today_plan_runtime` now owns deterministic normalization of latest plan payload context for workout-today (session list, session IDs, selected program ID, mesocycle, and deload) with structured decision trace.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now uses that helper before resume/session selection and state hydration flows, keeping route-level responsibilities to SQL reads and persistence.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_resume.py`, and `apps/api/tests/test_workout_session_state.py`: focused regressions passed after plan-runtime extraction.

Evidence (2026-03-09, workout-today log projection runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_today_log_runtime` now owns deterministic workout-log projection for workout-today resume and completion inputs (normalized `workout_id` rows plus selected-session `exercise_id`/`set_index` rows) with structured decision trace.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now delegates both resume and completion log projection inputs through that helper before calling resume/completion interpreters.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_resume.py`, and `apps/api/tests/test_workout_session_state.py`: focused regressions passed after log-runtime extraction.

Evidence (2026-03-09, workout log-set persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_workout_log_set_decision_runtime` now also shapes deterministic `ExerciseState` persistence payloads (`exercise_state_create_values`, `exercise_state_update_values`, `starting_load_runtime`, and `substitution_recommendation`) alongside existing log-set decision/runtime output.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now uses those core-engine payloads directly for `ExerciseState` create/update persistence while preserving in-router SQL writes and commit flow.
- Focused validation passed for this slice: `packages/core-engine/tests/test_intelligence.py -k \"prepare_workout_log_set_decision_runtime or prepare_workout_exercise_state_runtime\"` and `apps/api/tests/test_workout_logset_feedback.py`.

Evidence (2026-03-09, workout-progress completion projection extraction)
- `apps/api/app/routers/workout.py`: `GET /workout/{workout_id}/progress` now reuses `build_workout_today_log_runtime` for deterministic completion-log projection before completed-set aggregation.
- `apps/api/tests/test_workout_progress.py`, `apps/api/tests/test_workout_resume.py`, and `apps/api/tests/test_workout_session_state.py`: focused workout regressions passed after the progress-route extraction.

Evidence (2026-03-09, workout-summary progression lookup runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_summary_progression_lookup_runtime` now owns deterministic primary-exercise-id normalization from planned workout exercises for progression-state lookup, with structured decision trace.
- `apps/api/app/routers/workout.py`: `GET /workout/{workout_id}/summary` now delegates progression lookup ID shaping to that helper while retaining SQL reads and response validation in-router.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_summary.py`, and `apps/api/tests/test_workout_progress.py`: focused regressions passed after summary-runtime extraction.

Evidence (2026-03-09, workout-today progression lookup runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_workout_today_progression_lookup_runtime` now owns deterministic primary-exercise-id normalization from persisted workout session-state rows for progression-state lookup in workout-today, with structured decision trace.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now delegates that lookup-ID shaping to the shared helper before progression-state DB query.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_resume.py`, `apps/api/tests/test_workout_session_state.py`, and `apps/api/tests/test_workout_summary.py`: focused regressions passed after workout-today progression-runtime extraction.

Evidence (2026-03-09, plan guide summary resolution extraction)
- `packages/core-engine/core_engine/generation.py`: `resolve_program_guide_summary` now owns deterministic program-summary resolution for guide routes, including canonical `FileNotFoundError` on missing IDs.
- `apps/api/app/routers/plan.py`: `GET /plan/guides/programs/{program_id}` now delegates summary lookup to that helper while preserving HTTP error mapping and template loading in-router.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused engine/API regressions passed after guide-summary extraction.

Evidence (2026-03-09, coach-preview program-name resolution extraction)
- `packages/core-engine/core_engine/generation.py`: `resolve_program_display_name` now owns deterministic template-summary name resolution with canonical fallback to formatted program ID.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now delegates `program_name` resolution for response payload shaping to that helper instead of route-local summary/fallback logic.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused engine/API regressions passed for program-name resolution behavior in coach-preview flow.

Evidence (2026-03-09, weekly-review cycle persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_weekly_review_cycle_persistence_payload` now owns deterministic weekly-review persistence shaping for `faults.exercise_faults` and `storage_adjustments` with structured decision trace.
- `apps/api/app/routers/profile.py`: `POST /weekly-review` now delegates `WeeklyReviewCycle.faults` and `WeeklyReviewCycle.adjustments` payload preparation to that helper while keeping SQL persistence and HTTP contracts in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: focused engine/API regressions passed after weekly-review persistence extraction.

Evidence (2026-03-09, soreness persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_soreness_entry_persistence_payload` now owns deterministic soreness entry persistence payload shaping (entry date, copied severity-by-muscle mapping, and notes) for create/update flows.
- `apps/api/app/routers/profile.py`: `POST /soreness` and `PUT /soreness/{entry_id}` now delegate persistence payload normalization to that helper while retaining SQL reads/writes and HTTP error mapping in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_recovery_measurements.py`: focused engine/API regressions passed after soreness payload extraction.

Evidence (2026-03-09, body-measurement persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_body_measurement_create_payload` and `build_body_measurement_update_payload` now own deterministic body-measurement persistence shaping for create and partial-update flows.
- `apps/api/app/routers/profile.py`: `POST /body-measurements` and `PUT /body-measurements/{entry_id}` now delegate payload preparation/patch shaping to those helpers while preserving SQL persistence and HTTP error mapping in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_recovery_measurements.py`: focused engine/API regressions passed after body-measurement payload extraction.

Evidence (2026-03-09, optional rule-set loading extraction)
- `packages/core-engine/core_engine/generation.py`: `resolve_optional_rule_set` now owns deterministic optional rule-set loading with linked-template resolution and `FileNotFoundError` fallback-to-`None`.
- `apps/api/app/routers/plan.py` and `apps/api/app/routers/workout.py`: coach-preview/generate-week and workout today/log-set/summary rule-set loading now delegate to that helper instead of route-local linked-template fallback logic.
- `packages/core-engine/tests/test_generation.py`, `apps/api/tests/test_program_catalog_and_selection.py`, and `apps/api/tests/test_workout_session_state.py`/`test_workout_summary.py`/`test_workout_resume.py`: focused regressions passed after optional rule-set extraction.

Evidence (2026-03-09, profile date-window runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_profile_date_window_runtime` now owns shared start/end date-window runtime shaping for profile recovery list endpoints.
- `apps/api/app/routers/profile.py`: `GET /soreness` and `GET /body-measurements` now delegate date-window runtime prep to that helper before applying SQL filters.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_recovery_measurements.py`, and `apps/api/tests/test_weekly_review.py`: focused regressions passed after date-window runtime extraction.

Evidence (2026-03-09, profile upsert persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_profile_upsert_persistence_payload` now owns profile upsert persistence-field shaping, including selected-program defaulting and payload copy normalization.
- `apps/api/app/routers/profile.py`: `POST /profile` now delegates persistence payload shaping to that helper before ORM persistence.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_profile_training_state.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`: focused regressions passed after profile upsert extraction.

Evidence (2026-03-09, profile program recommendation input extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_profile_program_recommendation_inputs` now owns fallback input shaping for profile recommendation/switch runtime (`current_program_id`, `days_available`, `split_preference`, and latest-plan payload coercion).
- `apps/api/app/routers/profile.py`: `/profile/program-recommendation` and `/profile/program-switch` now delegate those normalized runtime inputs to the helper before recommendation/switch interpreters run.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_recommendation_and_switch.py`: focused regressions passed after recommendation input extraction.

Evidence (2026-03-09, weekly-checkin response payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_weekly_checkin_response_payload` now owns deterministic weekly-checkin response shaping (`status` + nutrition-phase fallback).
- `apps/api/app/routers/profile.py`: `POST /weekly-checkin` now delegates response payload shaping to that helper while keeping SQL writes in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_checkin.py`: focused regressions passed after weekly-checkin response extraction.

Evidence (2026-03-09, workout log-set request runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: `prepare_workout_log_set_request_runtime` now owns deterministic log-set request normalization (`primary_exercise_id` fallback plus normalized request fields).
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now consumes that runtime payload before persistence and interpreter calls.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_logset_feedback.py`, and `apps/api/tests/test_workout_session_state.py`: focused regressions passed after request-runtime extraction.

Evidence (2026-03-09, coaching recommendation timeline payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `normalize_coaching_recommendation_timeline_limit` now owns deterministic timeline limit clamping, and `build_coaching_recommendation_timeline_payload` now owns row-to-entry normalization (including non-dict recommendation payload coercion).
- `apps/api/app/routers/plan.py`: `GET /plan/intelligence/recommendations` now delegates timeline limit normalization and timeline payload shaping to those helpers while keeping SQL reads and response validation in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after timeline extraction.

Evidence (2026-03-09, generate-week runtime input payload extraction)
- `packages/core-engine/core_engine/generation.py`: `prepare_generate_week_plan_runtime_inputs` now owns deterministic `generate_week_plan` request payload shaping from normalized generation runtime plus profile context.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` now delegates its `generate_week_plan` call-input normalization to that helper while keeping SQL fan-in, template/rule loading, and persistence in-router.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_program_catalog_and_selection.py`: focused regressions passed after generate-week input extraction.

Evidence (2026-03-09, profile response payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_profile_response_payload` now owns deterministic `GET /profile` fallback/default payload shaping.
- `apps/api/app/routers/profile.py`: `GET /profile` now delegates response payload shaping to that helper while keeping auth and response validation in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_profile_dev_wipe.py`: focused regressions passed after profile response extraction.

Evidence (2026-03-09, workout plan-context normalization extraction)
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_plan_context` now owns workout-plan row payload normalization and `resolve_workout_plan_reference` orchestration for session/exercise/program context resolution.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set`, `GET /workout/{workout_id}/progress`, and `GET /workout/{workout_id}/summary` now delegate plan-context normalization to that helper while keeping SQL reads and persistence in-router.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_logset_feedback.py`, `apps/api/tests/test_workout_progress.py`, and `apps/api/tests/test_workout_summary.py`: focused regressions passed after plan-context extraction.

Evidence (2026-03-09, workout-today latest-plan payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `resolve_workout_today_plan_payload` now owns latest workout-plan row selection/payload normalization for workout-today runtime preparation.
- `apps/api/app/routers/workout.py`: `GET /workout/today` now delegates latest-plan payload selection/coercion to that helper while keeping SQL reads and HTTP 404 mapping in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_workout_resume.py`: focused regressions passed after workout-today plan payload extraction.

Evidence (2026-03-09, frequency adaptation sovereign trace-contract hardening)
- `packages/core-engine/core_engine/intelligence.py`: frequency adaptation preview/apply interpreters now emit stricter structured traces with explicit `version`, ordered `steps`, and machine-readable `outcome.reason_code`, and apply reuses resolved preview context for weak-area/recovery fields.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after trace-contract hardening.

Evidence (2026-03-09, canonical weak-area bonus-slot rule consumption)
- `packages/core-engine/core_engine/intelligence.py`: frequency adaptation preview now reads `frequency_adaptation_rules.weak_area_bonus_slots` from canonical onboarding package rules when shaping weak-area overlays.
- `packages/core-engine/core_engine/onboarding_adaptation.py`: adaptation scoring now consumes weak-area desired extra-slot signals per muscle instead of treating weak-area pressure as a single fixed boost.
- `packages/core-engine/tests/test_intelligence.py`, `packages/core-engine/tests/test_onboarding_adaptation.py`, and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after rules-signal extraction.

Evidence (2026-03-09, doctrine deload-cadence extraction improvement)
- `importers/pdf_doctrine_rules_v1.py`: rule distillation now extracts explicit `deload every N weeks` doctrine hints into typed `deload_rules.scheduled_every_n_weeks` instead of relying solely on intro-week fallback heuristics.
- `apps/api/tests/test_pdf_doctrine_rules_v1.py`: focused distiller regressions passed including the new scheduled-deload-cadence extraction case.

Evidence (2026-03-09, doctrine repeat-failure trigger extraction improvement)
- `importers/pdf_doctrine_rules_v1.py`: rule distillation now extracts explicit repeat-failure substitution thresholds (`after N failed exposures`) into typed `substitution_rules.repeat_failure_trigger` values (numeric `switch_after_N_failed_exposures` form), with existing default fallback retained when no explicit doctrine signal is present.
- `apps/api/tests/test_pdf_doctrine_rules_v1.py`: focused distiller regressions passed including the new repeat-failure threshold extraction case.
- `packages/core-engine/tests/test_rules_runtime.py`: focused rules-runtime regressions passed for numeric repeat-failure trigger threshold parsing compatibility.

Evidence (2026-03-09, doctrine early-deload trigger extraction improvement)
- `importers/pdf_doctrine_rules_v1.py`: rule distillation now extracts explicit early-deload trigger variants (`three consecutive under target sessions`) into typed `deload_rules.early_deload_trigger`, retaining canonical fallback when doctrine does not specify a variant.
- `apps/api/tests/test_pdf_doctrine_rules_v1.py`: focused distiller regressions passed including the new early-deload trigger extraction case.
- `packages/core-engine/tests/test_rules_runtime.py`: focused rules-runtime regressions passed for `three_consecutive_under_target_sessions` trigger behavior under low-fatigue underperformance.

Evidence (2026-03-09, doctrine fatigue-threshold extraction improvement)
- `importers/pdf_doctrine_rules_v1.py`: rule distillation now extracts explicit fatigue-threshold trigger text (`session RPE avg >= X for N exposures`) into normalized typed `fatigue_rules.high_fatigue_trigger.conditions` strings, retaining canonical fallback when doctrine does not specify a threshold.
- `importers/pdf_doctrine_rules_v1.py`: fatigue-rule provenance now prefers explicit fatigue-threshold excerpts for `source_sections` when present, improving traceability of rule grounding.
- `apps/api/tests/test_pdf_doctrine_rules_v1.py`: focused distiller regressions passed including the explicit fatigue-threshold extraction case.
- `packages/core-engine/tests/test_rules_runtime.py`: focused rules-runtime regressions passed, confirming extracted fatigue-threshold condition strings remain runtime-compatible.

Evidence (2026-03-09, frequency-adaptation decision family extraction start)
- `packages/core-engine/core_engine/decision_frequency_adaptation.py`: frequency-adaptation preview/apply and adaptation persistence payload builders now live in a dedicated decision-family module rather than being owned only by `intelligence.py`.
- `packages/core-engine/core_engine/decision_frequency_adaptation.py`: active adaptation state resolution/application helpers now also live in that same module (`resolve_active_frequency_adaptation_runtime`, `apply_active_frequency_adaptation_runtime`).
- `packages/core-engine/core_engine/intelligence.py`: frequency-adaptation entry points now delegate to the dedicated decision-family module, reducing direct decision-body sprawl in the intelligence God module while preserving API behavior.
- `packages/core-engine/core_engine/__init__.py`: frequency-adaptation public exports are now sourced from the dedicated decision-family module.
- `packages/core-engine/tests/test_decision_frequency_adaptation.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, weekly-review decision family extraction start)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review window/status/submit/persistence utility functions now live in a dedicated decision-family module.
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review decision interpretation and decision-payload builders now also live in that dedicated module (`interpret_weekly_review_decision`, `build_weekly_review_decision_payload`).
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review plan-adjustment application helpers now also live in that module (`apply_weekly_review_adjustments_to_plan` and its helper chain for set/weight override projection + adaptive-review payload shaping).
- `packages/core-engine/core_engine/intelligence.py`: weekly-review utility entry points now delegate to the dedicated decision-family module, reducing `intelligence.py` ownership while preserving route behavior.
- `packages/core-engine/core_engine/intelligence.py`: extracted weekly-review helper duplicates (guidance/rationale/global-adjustment/override helpers) were removed from `intelligence.py` after delegation, completing this slice’s ownership cleanup without route contract changes.
- `packages/core-engine/core_engine/__init__.py`: extracted weekly-review utility and plan-adjustment exports are now sourced from the dedicated decision-family module.
- `packages/core-engine/tests/test_decision_weekly_review.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-preview decision family extraction start)
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview response payload and recommendation-record-field shaping now live in a dedicated decision-family module (`build_coach_preview_payloads`, `build_coach_preview_recommendation_record_fields`).
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-apply source/runtime prep internals now also live in that module (`prepare_coaching_apply_runtime_source`, `prepare_phase_apply_runtime`, `prepare_specialization_apply_runtime`) with callback-injected decision/apply record hooks.
- `packages/core-engine/core_engine/intelligence.py`: those coach-preview payload helpers now delegate to the dedicated decision module, reducing additional payload-shaping ownership in `intelligence.py`.
- `packages/core-engine/core_engine/intelligence.py`: stable public signatures for apply-phase/specialization runtime prep remain wrapper-owned while delegating low-level prep logic to the decision module, preserving router call contracts.
- `packages/core-engine/core_engine/__init__.py`: coach-preview payload-shaping exports are sourced from `decision_coach_preview.py`; apply-runtime prep exports continue to route through the stable `intelligence.py` wrappers.
- `packages/core-engine/tests/test_decision_coach_preview.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, plan generate-week runtime assembly extraction)
- `packages/core-engine/core_engine/generation.py`: `prepare_plan_generation_decision_runtime` now owns canonical training-state assembly wiring into `resolve_week_generation_runtime_inputs` for generate-week runtime preparation, with structured trace output.
- `apps/api/app/routers/plan.py`: `_prepare_plan_generation_runtime` now keeps SQL reads only and delegates deterministic runtime payload prep to that core-engine helper.
- `packages/core-engine/core_engine/generation.py`: `prepare_frequency_adaptation_decision_runtime` now exposes top-level `context_trace`, preserving the adaptation request-context trace contract expected by generation runtime tests.
- `packages/core-engine/tests/test_generation.py`, `apps/api/tests/test_plan_intelligence_api.py`, `apps/api/tests/test_program_catalog_and_selection.py`, and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after this extraction.

Evidence (2026-03-09, adaptation onboarding program-id resolution extraction)
- `packages/core-engine/core_engine/generation.py`: `resolve_onboarding_program_id` now owns linked-template onboarding program ID resolution for adaptation flows.
- `apps/api/app/routers/plan.py`: adaptation preview/apply now delegate onboarding linked-program ID resolution to that helper before onboarding package loading.
- `packages/core-engine/tests/test_generation.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after onboarding program-id extraction.

Evidence (2026-03-09, adaptation persistence payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_frequency_adaptation_persistence_state` now owns apply-flow persistence-state normalization.
- `packages/core-engine/core_engine/intelligence.py`: `build_generated_week_adaptation_persistence_payload` now owns generate-week adaptation-state persistence shaping (`state_updated` + `next_state`).
- `apps/api/app/routers/plan.py`: adaptation apply and generate-week persistence writes now delegate payload shaping to those helpers.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after adaptation persistence extractions.

Evidence (2026-03-09, weekly-checkin/weekly-review profile payload extraction)
- `packages/core-engine/core_engine/intelligence.py`: `build_weekly_checkin_persistence_payload` now owns weekly-checkin entry payload shaping.
- `packages/core-engine/core_engine/intelligence.py`: `build_weekly_review_user_update_payload` now owns weekly-review user profile update payload shaping.
- `packages/core-engine/core_engine/intelligence.py`: `prepare_weekly_review_log_window_runtime` now owns previous-week half-open workout-log window timestamp shaping.
- `apps/api/app/routers/profile.py`: weekly-checkin and weekly-review now delegate those payload/window normalization seams to core-engine while keeping SQL/persistence in-router.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_weekly_review.py`: focused regressions passed after weekly-checkin/weekly-review payload extraction.

Evidence (2026-03-09, weekly-review performance-summary decision-family extraction)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review summary derivation now also lives in this module via `summarize_weekly_review_performance` and `build_weekly_review_performance_summary`, including planned-vs-performed aggregation, exercise fault scoring, and structured trace packaging.
- `packages/core-engine/core_engine/intelligence.py`: weekly-review summary entrypoints now delegate to the decision-family module wrappers, reducing direct weekly-review ownership in the intelligence module while preserving router contracts.
- `packages/core-engine/core_engine/__init__.py`: package exports for weekly-review performance summary helpers are now sourced from `decision_weekly_review.py` to match module ownership boundaries.
- `packages/core-engine/core_engine/intelligence.py`: duplicate weekly-review summary helper internals were removed after delegation, leaving `decision_weekly_review.py` as the single owner for that summary/fault-scoring decision chain.
- `packages/core-engine/tests/test_decision_weekly_review.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-apply commit runtime extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: apply confirm-path commit runtime now has dedicated helpers (`prepare_applied_coaching_recommendation_commit_runtime`, `finalize_applied_coaching_recommendation_commit_runtime`) for deterministic record-value shaping and post-flush response/recommendation payload finalization.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/public export surface now includes those commit-runtime helpers for router consumption.
- `apps/api/app/routers/plan.py`: apply-phase and apply-specialization confirm paths now share the commit-runtime helper flow instead of duplicated route-local payload wiring.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-apply request runtime branch extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: apply decision-request branch runtime prep now also lives in this module via `prepare_coaching_apply_decision_runtime` (source-runtime normalization, phase/specialization argument shaping, and trace metadata).
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/public export surface now includes `prepare_coaching_apply_decision_runtime` for router usage.
- `apps/api/app/routers/plan.py`: apply-phase/apply-specialization now share this helper for source-runtime branch wiring, removing duplicated route-local field unpacking before interpreter runtime prep.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-apply commit payload-key mapping extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: apply commit-runtime payload-key selection now also lives in this module via `prepare_coaching_apply_commit_runtime` (`phase` -> `phase_transition`, `specialization` -> `specialization`) with unsupported-kind guardrails.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/public export surface now includes `prepare_coaching_apply_commit_runtime` for router usage.
- `apps/api/app/routers/plan.py`: apply-phase/apply-specialization confirm paths now share this helper for commit-runtime preparation, removing duplicated route-local payload-key mapping.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-apply route branching runtime extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: apply route branching runtime now also lives in this module via `prepare_coaching_apply_route_runtime`, unifying preflight response payload selection and confirm-path commit-runtime preparation behind one deterministic helper.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/public export surface now includes `prepare_coaching_apply_route_runtime` for router usage.
- `apps/api/app/routers/plan.py`: apply-phase/apply-specialization now share this helper for preflight/confirm branching, removing remaining duplicated route-local branching glue while keeping DB writes and HTTP mapping in-router.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, weekly-review submit persistence-value extraction)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review submit persistence value shaping now also lives in this module via `prepare_weekly_review_submit_persistence_values`, producing deterministic `WeeklyCheckin` and `WeeklyReviewCycle` constructor payloads plus trace metadata.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_weekly_review_submit_persistence_values`.
- `apps/api/app/routers/profile.py`: weekly-review submit now delegates checkin/review constructor value preparation to that helper, removing remaining route-local persistence field wiring while keeping SQL writes in-router.
- `packages/core-engine/tests/test_decision_weekly_review.py` and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-preview commit runtime extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview commit runtime now also lives in this module via `prepare_coach_preview_commit_runtime` and `finalize_coach_preview_commit_runtime`, centralizing recommendation-record constructor payload shaping and post-flush response/recommendation payload finalization.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/public export surface now includes these coach-preview commit runtime helpers for router usage.
- `apps/api/app/routers/plan.py`: coach-preview now delegates record constructor payload prep and post-flush payload finalization to shared helpers, reducing route-local deterministic commit wiring while keeping DB writes in-router.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, workout log-set exercise-state runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: workout log-set exercise-state runtime now also lives in this module via `prepare_workout_exercise_state_runtime`, centralizing existing-state normalization, first-exposure starting-load fallback, progression update payload shaping, and repeat-failure substitution payload preparation.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_workout_exercise_state_runtime`.
- `apps/api/app/routers/workout.py`: log-set now delegates exercise-state runtime prep to that helper; route retains ORM query/create/add/commit while deterministic state field mapping moves to core-engine.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_logset_feedback.py`, `apps/api/tests/test_workout_summary.py`, and `apps/api/tests/test_workout_progress.py`: focused regressions passed after extraction.

Evidence (2026-03-09, frequency-adaptation route runtime extraction)
- `packages/core-engine/core_engine/decision_frequency_adaptation.py`: adaptation preview/apply route orchestration now also lives in this module via `prepare_frequency_adaptation_route_runtime`, centralizing shared runtime-argument shaping, preview/apply interpreter dispatch, and apply response/persistence payload shaping.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper and export surface now include `prepare_frequency_adaptation_route_runtime`.
- `apps/api/app/routers/plan.py`: adaptation preview/apply endpoints now share this helper instead of duplicating deterministic interpreter argument wiring and apply payload construction; routes keep SQL reads, onboarding package load, persistence commit, and HTTP mapping.
- `packages/core-engine/tests/test_decision_frequency_adaptation.py` and `apps/api/tests/test_program_frequency_adaptation_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach-preview route runtime extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: coach-preview route composition now also lives in this module via `prepare_coach_preview_route_runtime`, centralizing preview interpreter dispatch and commit-runtime preparation behind one decision-family helper.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_coach_preview_route_runtime`.
- `apps/api/app/routers/plan.py`: `POST /plan/intelligence/coach-preview` now delegates deterministic preview/commit composition to this helper instead of route-local wiring; route keeps SQL reads, template/rule loading, DB persistence, and HTTP mapping.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, profile recommendation route-runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: profile recommendation route composition now also lives in this module via `prepare_profile_program_recommendation_route_runtime`, centralizing fallback input shaping + recommendation runtime prep behind one deterministic helper.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_profile_program_recommendation_route_runtime`.
- `apps/api/app/routers/profile.py`: program recommendation and program switch endpoints now share this helper instead of duplicating recommendation input/runtime wiring.
- `packages/core-engine/tests/test_intelligence.py` and `apps/api/tests/test_program_recommendation_and_switch.py`: focused regressions passed after extraction.

Evidence (2026-03-09, weekly-review submit route-runtime extraction)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review submit route composition now also lives in this module via `prepare_weekly_review_submit_route_runtime`, centralizing decision payload shaping, review persistence payload shaping, user update payload shaping, submit persistence value shaping, and final response payload shaping.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_weekly_review_submit_route_runtime`.
- `apps/api/app/routers/profile.py`: `POST /weekly-review` now reuses this helper instead of route-local composition across multiple weekly-review decision/persistence builders.
- `packages/core-engine/tests/test_decision_weekly_review.py` and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-09, coach apply route-finalize extraction)
- `packages/core-engine/core_engine/decision_coach_preview.py`: apply finalize branching now also lives in this module via `prepare_coaching_apply_route_finalize_runtime`, centralizing preflight response passthrough vs confirm-path commit finalization and recommendation payload shaping.
- `packages/core-engine/core_engine/intelligence.py` and `packages/core-engine/core_engine/__init__.py`: stable wrapper/export surface now includes `prepare_coaching_apply_route_finalize_runtime`.
- `apps/api/app/routers/plan.py`: apply-phase/apply-specialization now reuse this helper for deterministic final response/recommendation payload preparation after route runtime assembly and optional DB flush.
- `packages/core-engine/tests/test_decision_coach_preview.py` and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

Evidence (2026-03-09, workout session-state upsert runtime extraction)
- `packages/core-engine/core_engine/intelligence.py`: workout session-state upsert payload composition now also lives in this module via `prepare_workout_session_state_upsert_runtime`, centralizing create-default seeding and persisted update/live recommendation payload preparation.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes `prepare_workout_session_state_upsert_runtime`.
- `apps/api/app/routers/workout.py`: `_upsert_workout_session_state` now delegates deterministic state payload composition to this helper while keeping ORM fetch/create/add in-router.
- `packages/core-engine/tests/test_intelligence.py`, `apps/api/tests/test_workout_session_state.py`, and `apps/api/tests/test_workout_logset_feedback.py`: focused regressions passed after extraction.

Evidence (2026-03-09, weekly-review status/summary route-runtime extraction)
- `packages/core-engine/core_engine/decision_weekly_review.py`: weekly-review route composition now also includes `prepare_weekly_review_summary_route_runtime` and `prepare_weekly_review_status_route_runtime`, centralizing previous-week summary payload shaping and weekly-review status response payload/window shaping.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes both weekly-review status/summary route-runtime helpers.
- `apps/api/app/routers/profile.py`: `GET /weekly-review/status` and `_collect_previous_week_performance_summary` now reuse those helpers instead of route-local summary/status payload composition.
- `packages/core-engine/tests/test_decision_weekly_review.py` and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-09, plan apply-route orchestration consolidation)
- `apps/api/app/routers/plan.py`: apply-phase and apply-specialization now share `_apply_coaching_decision_route`, consolidating repeated route orchestration (recommendation lookup, apply runtime dispatch, preflight-vs-confirm branching, optional applied-record flush/commit, and response payload return).
- `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after consolidation (`9` tests).

Evidence (2026-03-10, workout route-runtime extraction)
- `packages/core-engine/core_engine/decision_workout_session.py`: workout route-runtime composition now also lives in a dedicated decision-family module via `prepare_workout_today_plan_route_runtime`, `prepare_workout_today_selection_route_runtime`, `prepare_workout_today_response_runtime`, `prepare_workout_progress_route_runtime`, and `prepare_workout_summary_route_runtime`, centralizing deterministic plan selection, resume selection, payload hydration, progress shaping, and summary lookup prep with structured traces.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes the new workout route-runtime helpers.
- `apps/api/app/routers/workout.py`: `GET /workout/today`, `GET /workout/{workout_id}/progress`, and `GET /workout/{workout_id}/summary` now delegate those deterministic composition paths to the workout decision-family helper while keeping SQL reads, optional rule-set loading, persistence, and HTTP error mapping in-router.
- `packages/core-engine/tests/test_decision_workout_session.py`, `apps/api/tests/test_workout_resume.py`, `apps/api/tests/test_workout_progress.py`, `apps/api/tests/test_workout_summary.py`, and `apps/api/tests/test_workout_session_state.py`: focused regressions passed after extraction.

Evidence (2026-03-10, generate-week route-runtime extraction)
- `packages/core-engine/core_engine/generation.py`: generate-week route-runtime composition now also includes `prepare_generate_week_scheduler_runtime`, `prepare_generate_week_review_lookup_runtime`, and `prepare_generate_week_finalize_runtime`, centralizing scheduler kwargs, `week_start` review lookup parsing, review-overlay/finalized-plan shaping, adaptation persistence shaping, and `WorkoutPlan` record values with structured traces.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes the new generate-week route-runtime helpers.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` now delegates route-local scheduler argument assembly, `week_start` parsing, finalized plan shaping, adaptation persistence payload shaping, and `WorkoutPlan` constructor payload wiring to those helpers while keeping SQL reads, review-cycle lookup, DB writes, and HTTP error mapping in-router.
- `packages/core-engine/tests/test_generation.py`, `apps/api/tests/test_program_catalog_and_selection.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`, and `apps/api/tests/test_weekly_review.py`: focused regressions passed after extraction.

Evidence (2026-03-10, completed workout-family route-runtime extraction)
- `packages/core-engine/core_engine/decision_workout_session.py`: the workout decision-family now also includes `prepare_workout_log_set_context_route_runtime`, `prepare_workout_log_set_decision_route_runtime`, `prepare_workout_session_state_route_runtime`, `prepare_workout_log_set_response_runtime`, `prepare_workout_today_progression_route_runtime`, and `prepare_workout_summary_response_runtime`, centralizing the remaining deterministic `log-set`, `today`, and `summary` route glue with structured traces.
- `packages/core-engine/core_engine/__init__.py`: package export surface now includes the expanded workout decision-family helpers.
- `apps/api/app/routers/workout.py`: `POST /workout/{workout_id}/log-set` now delegates request/context shaping, decision-runtime prep, session-state upsert payload shaping, and final response payload shaping to the workout decision-family helper; `GET /workout/today` now also delegates progression-id/rule-set prep there; `GET /workout/{workout_id}/summary` now also delegates final summary response shaping there.
- `packages/core-engine/tests/test_decision_workout_session.py`, `apps/api/tests/test_workout_resume.py`, `apps/api/tests/test_workout_progress.py`, `apps/api/tests/test_workout_summary.py`, `apps/api/tests/test_workout_session_state.py`, and `apps/api/tests/test_workout_logset_feedback.py`: focused regressions passed after the completed workout-family extraction.

Evidence (2026-03-10, program recommendation decision-family extraction)
- `packages/core-engine/core_engine/decision_program_recommendation.py`: program recommendation/switch ownership now lives in a dedicated decision-family module (`resolve_program_recommendation_candidates`, `recommend_program_selection`, `prepare_program_recommendation_runtime`, `prepare_profile_program_recommendation_route_runtime`, `build_program_switch_payload`, and `prepare_program_switch_runtime`), preserving structured candidate-resolution and selection traces.
- `packages/core-engine/core_engine/intelligence.py`: stable public entrypoints for those recommendation/switch helpers now delegate to the dedicated decision-family module so existing router and test imports keep the same surface while ownership moves out of the god module.
- `packages/core-engine/core_engine/__init__.py`: package exports for recommendation/switch helpers are now sourced from the dedicated decision-family module.
- `packages/core-engine/tests/test_decision_program_recommendation.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_program_recommendation_and_switch.py`: focused regressions passed after extraction.

Evidence (2026-03-10, progression decision-family extraction)
- `packages/core-engine/core_engine/decision_progression.py`: schedule adaptation, readiness scoring, progression action selection, progression rationale humanization, and phase-transition selection/humanization now live in a dedicated decision-family module.
- `packages/core-engine/core_engine/intelligence.py`: stable public entrypoints for schedule/progression/phase-transition helpers now delegate to the dedicated decision-family module so coach-preview and other consumers keep the existing import surface while ownership moves out of the god module.
- `packages/core-engine/core_engine/__init__.py`: package exports for those progression helpers are now sourced from the dedicated decision-family module.
- `packages/core-engine/tests/test_decision_progression.py`, `packages/core-engine/tests/test_intelligence.py`, and `apps/api/tests/test_plan_intelligence_api.py`: focused regressions passed after extraction.

### Task 2.2 - Gold End-To-End Runtime Path
- Selection -> generation -> logging -> evaluation -> adaptation.
- Status: STARTED

Evidence (2026-03-06)
- `apps/api/app/routers/plan.py`: `POST /plan/adaptation/apply` persists temporary adaptation state.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` consumes active adaptation state and applies temporary day-frequency reduction.
- `apps/api/tests/test_program_frequency_adaptation_api.py`: apply + generate-week countdown coverage.
- `apps/web/app/settings/page.tsx`: UI wiring for adaptation preview and apply actions.

## Priority 3 - Scale and Hardening

### Task 3.1 - Program Library Migration
- Expand canonical migration beyond gold sample.

### Task 3.2 - Scenario and Regression Expansion
- Add scenario suite for progression/fatigue/deload/substitution behavior.

### Task 3.3 - Import Archive Hygiene
- Keep imported template variants available for audit, not runtime selection.
- Status: STARTED

Evidence (2026-03-06)
- Imported templates moved to `programs/archive_imports/` with `programs/archive_imports/README.md`.
- Runtime catalog filtered in `apps/api/app/program_loader.py` to exclude archive/import variants.

### Task 3.4 - Onboarding Reliability Loop
- Ensure local test onboarding can recover from stale test users without manual DB operations.
- Status: DONE

Evidence (2026-03-06)
- `apps/api/app/routers/auth.py`: `POST /auth/dev/wipe-user` endpoint (config-gated dev reset).
- `apps/web/app/onboarding/page.tsx`: onboarding reset controls, actionable auth failure messaging, and browser-local draft autosave/restore (`Clear Saved Draft` support).
- `apps/api/tests/test_auth_password_reset.py`: wipe endpoint re-registration coverage.

### Task 3.5 - Screenshot Parity Translation
- Convert external onboarding references into implementable parity checklist tasks.
- Status: STARTED

Evidence (2026-03-06)
- `docs/redesign/Onboarding_Reference_Analysis_Batch1.md`: extracted intro + questionnaire flow structure and tracked field map from first screenshot batch.
- `docs/redesign/Onboarding_Reference_Analysis_Batch2.md`: extracted motivation/obstacle/frequency/name/account-transition/sync steps from second screenshot batch.
- `docs/redesign/Onboarding_Reference_Analysis_Batch3.md`: extracted notifications/location/equipment/experience/duration/days and workout-generation handoff from final screenshot batch.
- `docs/redesign/Onboarding_Reference_Process_Map.md`: consolidated sequence and deterministic-input map across all provided screenshot batches.

### Task 3.7 - Onboarding Funnel Refinement v1
- Replace single-page onboarding form with step-based low-friction funnel aligned with reference behavior.
- Status: DONE

Evidence (2026-03-06)
- `apps/web/app/onboarding/page.tsx`: intro slides, one-question-per-step flow, progress bar, skip for optional steps, account stage, browser-local draft restore, and workout bootstrap handoff.
- `apps/web/tests/onboarding.program.test.tsx`: onboarding draft restore regression coverage.
- `apps/api/app/models.py`: `onboarding_answers` persistence field.
- `apps/api/app/routers/profile.py`: profile upsert/get now writes and returns onboarding answers.
- `apps/api/alembic/versions/0012_user_onboarding_answers.py`: migration for onboarding answers persistence.

### Task 3.6 - Calendar Training History View
- Add a calendar page where the user can click previous days to inspect completed training for that date.
- Status: DONE

Evidence (2026-03-06)
- `apps/api/app/routers/history.py`: added `GET /history/calendar` (windowed day summaries, active-day totals, current/longest streaks).
- `apps/api/app/routers/history.py`: added `GET /history/day/{day}` day drill-down (workout/exercise/set-level performed detail plus planned-vs-performed set deltas when plan data exists).
- `apps/api/app/routers/history.py`: calendar day payload now includes program/muscle metadata and PR badge metadata; day detail includes planned exercise names/muscles and planned-only missed-day detail.
- `apps/web/app/history/page.tsx`: added clickable calendar grid, week/month window navigation, completion/program/muscle filters, previous-same-weekday jump, same-weekday delta comparison cards, PR badges, and selected-day detail panel.
- `apps/api/tests/test_history_calendar.py`: API coverage for calendar summaries and day detail.
- `apps/web/tests/history.calendar.test.tsx`: UI coverage for calendar click -> day detail flow, filters, window navigation, weekday jump, same-weekday comparison metrics, and missed-day planned detail rendering.

Scope
- Month and week calendar views with completion indicators.
- Click/tap a date to open full training detail for that day.
- Show performed exercises, sets/reps/weight, substitutions, and completion status.
- Show planned vs performed deltas when plan exists for that date.
- Include quick filters (program, muscle group, completed vs missed).
- Include streak and weekly consistency summaries in calendar context.

Stretch (post-MVP)
- DONE: personal records/best set badges surfaced on calendar days.
- DONE: fast jump to same weekday history (e.g., previous Mondays) for progression comparison.
## Recently Completed

- surfaced post-authored-sequence transition guidance in web coaching UI
- added lightweight internal tester docs for desktop/mobile browser dogfooding

## Next Likely Batch

1. run a focused responsive QA pass on the real web app against the tester runbook
2. tighten any mobile-browser layout issues in onboarding, today, weekly review, and history
3. keep broader doctrine/library migration separate from tester-readiness fixes
