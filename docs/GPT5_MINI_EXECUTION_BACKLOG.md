# GPT-5-mini Execution Backlog - Adaptive Coaching Rebuild

Last updated: 2026-03-09

## Priority 0 - Foundation (In Progress)

### Task 0.5 - Decision Runtime Sovereignty
- Move meaningful coaching decisions behind one authoritative interpreter path in `packages/core-engine`.
- Emit structured decision traces.
- Prevent legacy runtime paths from receiving new coaching behavior.
- Status: STARTED

Evidence (2026-03-07)
- `docs/AI_CONTINUATION_GOVERNANCE.md`: repository law for decision-runtime sovereignty, legacy containment, and trace requirements.
- `apps/api/app/routers/profile.py` and `packages/core-engine/core_engine/intelligence.py`: program recommendation is the first decision family being migrated behind a core-engine interpreter with a structured decision trace.

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
