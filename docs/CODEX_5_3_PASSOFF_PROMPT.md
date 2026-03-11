# Codex 5.3 Passoff Prompt

Last updated: 2026-03-11

Use the prompt below for the Codex 5.3 agent.

## Prompt

You are Codex 5.3 taking over active development on `/home/rocco/hypertrophyapp`.

You must continue the deterministic adaptive hypertrophy coaching rebuild without architectural drift.

Start by reading these docs in order:

1. `docs/AI_CONTINUATION_GOVERNANCE.md`
2. `docs/Master_Plan.md`
3. `docs/Architecture.md`
4. `docs/current_state_decision_runtime_map.md`
5. `docs/redesign/Adaptive_Coaching_Redesign.md`
6. `docs/GPT5_MINI_HANDOFF.md`
7. `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
8. `docs/Master_Plan_Checkmark_Audit.md`
9. `docs/CODEX_5_3_PASSOFF_PROMPT.md`

Then inspect these implementation files before changing code:

1. `packages/core-engine/core_engine/intelligence.py`
2. `packages/core-engine/core_engine/generation.py`
3. `packages/core-engine/core_engine/user_state.py`
4. `packages/core-engine/core_engine/rules_runtime.py`
5. `packages/core-engine/core_engine/decision_live_workout_guidance.py`
6. `packages/core-engine/core_engine/decision_workout_session.py`
7. `packages/core-engine/core_engine/decision_program_recommendation.py`
8. `packages/core-engine/core_engine/decision_progression.py`
9. `apps/api/app/models.py`
10. `apps/api/app/adaptive_schema.py`
11. `apps/api/app/routers/plan.py`
12. `apps/api/app/routers/profile.py`
13. `apps/api/app/routers/workout.py`

Your objective:

1. Keep moving meaningful deterministic coaching logic into authoritative decision-family modules inside `packages/core-engine`, and remove ambiguous ownership from `intelligence.py`.
2. Keep API routers limited to auth, SQL reads/writes, persistence, HTTP error mapping, and response validation.
3. Prefer canonical `UserTrainingState` whenever runtime context is needed for recommendations, generation, adaptation, recovery, adherence, progression, soreness, or history.
4. Preserve or add structured `decision_trace` output for migrated decision families.
5. Do not add broad new product features until the current authority-cleanup phase is complete.
6. Work in focused slices with targeted tests after each slice.

Non-negotiable constraints:

1. Do not move DB access into `packages/core-engine`.
2. Do not add runtime dependence on `docs/guides/*` artifacts.
3. Do not introduce new client-side coaching heuristics if deterministic API payloads already exist.
4. Do not do broad cleanup or style-only refactors.
5. Do not revisit already migrated seams unless a test proves regression or dead code remains.

Environment rules:

1. Use `apps/api/.venv/bin/python` directly. Do not rely on `source apps/api/.venv/bin/activate`; it may fail.
2. For focused API tests, run from `apps/api` with `TEST_DATABASE_URL=sqlite:///./test_local_<name>.sqlite3 apps/api/.venv/bin/python -m pytest <file>`.
3. For focused engine tests, run from `packages/core-engine` with `apps/api/.venv/bin/python -m pytest tests/test_intelligence.py -k <pattern>`.
4. Remove temporary SQLite files created by focused API runs.

What is already migrated and should be treated as established architecture:

1. Canonical `UserTrainingState` assembly in `packages/core-engine/core_engine/user_state.py` and `GET /profile/training-state`.
2. Canonical user-state consumption in frequency adaptation preview/apply, week-generation runtime inputs, coach-preview history/context, program recommendation, and program switch.
3. Weekly review window/status logic, summary preparation, decision packaging, and submit payload shaping.
4. Workout resume-state derivation, today-session selection, completed-set aggregation, summary runtime preparation, repeat-failure substitution payload shaping, planned exercise log-set normalization, session-state default seeding, session-state persistable payload preparation, and log-set response payload shaping.
5. Template loading/selection orchestration for coach-preview and generate-week.
6. Final generate-week returned-plan assembly through `build_generated_week_plan_payload`.
7. Workout route-runtime ownership in `packages/core-engine/core_engine/decision_workout_session.py`.
8. Program recommendation/switch ownership in `packages/core-engine/core_engine/decision_program_recommendation.py`.
9. Progression/readiness/phase-transition ownership in `packages/core-engine/core_engine/decision_progression.py`.

Latest completed slices in this branch:

1. `packages/core-engine/core_engine/decision_live_workout_guidance.py`
   - now owns live workout guidance, per-set feedback interpretation, hydrated guidance payloads, session-state guidance updates, and session-guidance summaries
2. `packages/core-engine/core_engine/decision_workout_session.py`
   - now owns the workout route family runtime composition for `today`, `progress`, `summary`, and `log-set` request/response shaping
3. `packages/core-engine/core_engine/decision_program_recommendation.py`
   - now owns program recommendation and program-switch decision/runtime preparation
4. `packages/core-engine/core_engine/decision_progression.py`
   - now owns schedule adaptation, readiness, progression action, and phase-transition logic
5. `packages/core-engine/core_engine/generation.py`
   - now owns generate-week route runtime preparation through dedicated helpers instead of route-local payload shaping
6. `docs/current_state_decision_runtime_map.md`
   - now records the current local-branch authority map and should be treated as the cleanup contract for the next phase
7. `apps/api/app/models.py`, `packages/core-engine/core_engine/user_state.py`, and `apps/api/app/adaptive_schema.py`
   - now carry first-class coaching `constraint_state` inputs (`days_available`, split/training/equipment preferences, weak areas, nutrition phase, session time budget, movement restrictions, near-failure tolerance)
8. `apps/api/app/models.py`, `packages/core-engine/core_engine/user_state.py`, and `apps/api/app/adaptive_schema.py`
   - now also carry weekly-checkin-backed `readiness_state` inputs (`sleep_quality`, `stress_level`, `pain_flags`, `recovery_risk_flags`)
9. `packages/core-engine/core_engine/decision_progression.py`, `packages/core-engine/core_engine/decision_coach_preview.py`, and `packages/core-engine/core_engine/generation.py`
   - coach-preview now consumes canonical `readiness_state` when `readiness_score` is omitted, and readiness traces now record that source
10. `packages/core-engine/core_engine/decision_weekly_review.py` and `apps/api/app/routers/profile.py`
   - weekly-review now consumes canonical `readiness_state` from the latest persisted check-in, and review traces record readiness-state penalty source
11. `packages/core-engine/core_engine/decision_progression.py`
   - now emits a first deterministic `stimulus_fatigue_response` snapshot that coach-preview traces carry end-to-end
   - that snapshot now also affects real progression/deaload decisions
12. `packages/core-engine/core_engine/generation.py` and `packages/core-engine/core_engine/scheduler.py`
   - generate-week now derives an SFR snapshot from canonical readiness/fatigue/adherence inputs, uses it for recovery-limited scheduler deloads, and surfaces structured substitution pressure/guidance on planned exercises
13. `packages/core-engine/core_engine/generation.py`, `packages/core-engine/core_engine/scheduler.py`, and `apps/api/app/routers/plan.py`
   - generate-week now threads canonical `progression_state_per_exercise` from persisted `ExerciseState` rows and can auto-substitute compatible exercises after repeat-failure thresholds, preserving `primary_exercise_id` and surfacing structured `repeat_failure_substitution`
14. `packages/core-engine/core_engine/decision_coach_preview.py`
   - now owns specialization-adjustment and program-media/warmup summarization helpers; `intelligence.py` keeps compatibility wrappers only
15. `packages/core-engine/core_engine/decision_workout_session.py`
   - now owns workout performance summary, log-set request/runtime shaping, session-state defaults/persistence helpers, workout-today plan/log/progression runtime helpers, and repeat-failure substitution payload shaping on the package surface and route-runtime path
16. `apps/api/app/program_loader.py`
   - now supports the adaptive gold sample as a first-class runtime program by adapting `programs/gold/adaptive_full_body_gold_v0_1.json` into the current runtime template contract and resolving its matching gold rule set through the standard loader boundary
   - now also hydrates adaptive-gold exercise metadata and valid substitutions from the matching onboarding package so the gold runtime path can auto-substitute with canonical substitute ids/names instead of raw fallback ids
17. `apps/api/tests/test_program_catalog_and_selection.py`
   - now proves five adaptive-gold runtime scenarios at the API layer: base generate-week, persisted `log-set` -> `weekly-review` loop, repeat-failure substitution, canonical-readiness `early_sfr_recovery` deload, and saved weekly-review overlay carry-forward into the next generated gold week
18. `apps/api/tests/test_workout_session_state.py`
   - now proves adaptive-gold workout continuity: `GET /workout/today` reflects generated-week repeat-failure substitutions on the gold program, and gold `log-set` substitution guidance persists into the next `today` payload
19. `packages/core-engine/core_engine/scheduler.py`
   - substitution metadata fallback now preserves original movement/equipment/muscle metadata when a substitute has only partial onboarding metadata, and the current adaptive-gold proof now covers both exercise families present in the sample
20. `programs/gold/adaptive_full_body_gold_v0_1.json`
   - the authored adaptive-gold sample now includes a third vertical-pull slot (`lat_pulldown_wide`), and loader/generation/workout tests now prove substitution continuity for that third family as well
   - the authored adaptive-gold sample now also includes a fourth lower-body slot (`hack_squat`), and loader/generation/workout tests now prove substitution continuity for that fourth family as well
   - the authored adaptive-gold sample now also includes a fifth core/ab slot (`cable_crunch`), and focused loader/generation/workout tests now prove that the core slot survives the runtime path when cable equipment is available
   - the authored adaptive-gold sample now also includes a sixth hinge/posterior-chain slot (`romanian_deadlift`), and focused loader/generation/workout tests now prove that the hinge slot survives the runtime path when barbell/dumbbell equipment is available
   - the authored adaptive-gold sample now also includes onboarding-backed accessory/weak-point chest and hamstring slots (`weak_chest_cable_fly`, `weak_ham_leg_curl`), and focused loader/generation/workout tests now prove that those weak-area slots survive the runtime path when cable/machine equipment is available
   - the canonical gold onboarding library now also includes arm-isolation entries (`dumbbell_curl_incline`, `triceps_pushdown_rope`), and the authored adaptive-gold sample plus focused loader/generation/workout tests now prove that those biceps/triceps slots survive the runtime path with canonical metadata
   - the adaptive-gold runtime now starts from a real authored five-day source (`Full Body #1-#4` plus `Arms & Weak Points`), and adaptive-gold runtime loading now preserves `day_role` plus per-slot `slot_role` through the canonical loader boundary
   - focused scheduler/API/workout tests now prove weak-point and primary-compound preservation under constrained time/frequency: the dedicated weak-point day survives where possible and primary compound patterns survive five-day-to-three-day compression through dropped-session exercise merging
   - the adaptive-gold sample now preserves `authored_weeks` through the runtime loader path and extends to a full 10-week authored mesocycle aligned to the onboarding sequence `build_a / build_b / build_a / build_b / build_a / deload / intens_a / intens_b / intens_a / intens_b`
   - adaptive/template schemas preserve optional `week_role`, and scheduler records `mesocycle.authored_week_index` / `mesocycle.authored_week_role` while preferring `authored_deload` as the primary reason when authored and generic deload cadence overlap
   - focused loader/API tests now prove week-2 Build-B selection (`6-9`), week-6 authored deload selection, and weeks 8 and 10 intensification selection (`4-6`) on the gold runtime path
   - scheduler now also makes post-week-10 behavior explicit: once the authored sequence is exhausted, generated-week holds the final authored week as the deterministic fallback while surfacing `authored_sequence_complete`, `phase_transition_pending`, and `post_authored_behavior == "hold_last_authored_week"` in `mesocycle`
   - focused engine/API tests now prove that post-week-10 contract on the gold path instead of leaving it implicit
   - canonical training state now preserves that same post-week-10 context in `generation_state.latest_mesocycle`, coach-preview now surfaces it as `phase_transition.transition_pending` with `recommended_action == "rotate_program"`, and program recommendation now prioritizes rotating off the completed authored sequence before simpler day-adaptation upgrades
   - adaptive-gold weak-point preservation under constrained time/frequency still remains covered on top of the longer authored mesocycle

Current best next seam:

1. Use `docs/current_state_decision_runtime_map.md` as the cleanup contract before changing code.
2. Keep `packages/core-engine/core_engine/decision_live_workout_guidance.py` authoritative and do not add new live-guidance logic back into `intelligence.py`.
3. Generate-week now already consumes canonical `progression_state_per_exercise` and repeat-failure substitution; do not re-implement that path in routers or wrappers.
4. The workout family is now façade-only in `intelligence.py`; do not reintroduce workout ownership there.
5. The Phase 1 workbook import pipeline is no longer the blocker:
   - real workbook headers parse correctly
   - Excel `m-d` serial cells decode correctly
   - superset prefixes no longer pollute exercise ids
   - key workbook exercise metadata is now materially corrected
   - the loader can flatten source-backed multi-phase adaptive bundles
6. The next high-value seam is live gold-artifact migration:
   - align `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
   - align `programs/gold/adaptive_full_body_gold_v0_1.json`
   - preserve already-proven runtime semantics while moving toward the real workbook/PDF exercise lineup and intent before broader user testing or wider library migration

Recommended workflow:

1. Read the docs and implementation files listed above.
2. Confirm the current authoritative owner for the target family in `docs/current_state_decision_runtime_map.md`.
3. Prefer extending canonical persistence/state contracts and existing decision-family modules rather than adding more mixed ownership to `intelligence.py`.
4. Make the smallest state/model expansion that materially improves coaching quality without adding broad new product surface area.
5. Run focused engine and/or API tests tied to that seam.
6. If the boundary meaningfully changes, update:
   - `docs/current_state_decision_runtime_map.md`
   - `docs/GPT5_MINI_HANDOFF.md`
   - `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
   - `docs/Master_Plan_Checkmark_Audit.md` when evidence materially changes
7. Clean up temporary SQLite files.
8. Report exactly what changed, what passed, whether `mini_validate` was run, and what the next likely seam is.

Validation guidance:

1. Use focused tests first.
2. Run `./scripts/mini_validate.sh` only after a cluster of meaningful changes or if you touch a shared contract with broader impact.
3. If a focused test fails, fix the root cause rather than loosening the assertion unless the assertion is clearly invalid.

Output expectations after each slice:

1. State the seam selected and why it was chosen.
2. List the files changed.
3. List the focused tests that passed.
4. State whether `mini_validate` was run.
5. Name the next likely seam, with explicit reference to the authority map when ownership changes.
