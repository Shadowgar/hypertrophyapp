# Codex 5.3 Passoff Prompt

Last updated: 2026-03-09

Use the prompt below for the Codex 5.3 agent.

## Prompt

You are Codex 5.3 taking over active development on `/home/rocco/hypertrophyapp`.

You must continue the deterministic adaptive hypertrophy coaching rebuild without architectural drift.

Start by reading these docs in order:

1. `docs/AI_CONTINUATION_GOVERNANCE.md`
2. `docs/Master_Plan.md`
3. `docs/redesign/Adaptive_Coaching_Redesign.md`
4. `docs/GPT5_MINI_HANDOFF.md`
5. `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
6. `docs/Master_Plan_Checkmark_Audit.md`
7. `docs/CODEX_5_3_PASSOFF_PROMPT.md`

Then inspect these implementation files before changing code:

1. `packages/core-engine/core_engine/intelligence.py`
2. `packages/core-engine/core_engine/generation.py`
3. `packages/core-engine/core_engine/user_state.py`
4. `packages/core-engine/core_engine/rules_runtime.py`
5. `apps/api/app/adaptive_schema.py`
6. `apps/api/app/routers/plan.py`
7. `apps/api/app/routers/profile.py`
8. `apps/api/app/routers/workout.py`

Your objective:

1. Keep moving meaningful router-owned deterministic logic, normalization, and payload preparation into `packages/core-engine`.
2. Keep API routers limited to auth, SQL reads/writes, persistence, HTTP error mapping, and response validation.
3. Prefer canonical `UserTrainingState` whenever runtime context is needed for recommendations, generation, adaptation, recovery, adherence, progression, soreness, or history.
4. Preserve or add structured `decision_trace` output for migrated decision families.
5. Work in small slices with focused tests after each slice.

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

Latest completed slices in this branch:

1. `packages/core-engine/core_engine/intelligence.py`
   - `build_workout_performance_summary`
   - `build_repeat_failure_substitution_payload`
   - `build_workout_today_session_state_payloads`
   - `resolve_workout_log_set_plan_context`
   - `build_workout_session_state_defaults`
   - `prepare_workout_session_state_persistence_payload`
2. `apps/api/app/routers/workout.py`
   - resolves stored workout plan context once per request
   - delegates summary prep, substitution payload shaping, planned exercise normalization, and session-state prep to core-engine
3. `apps/api/app/routers/plan.py`
   - `plan_generate_week` now centralizes its canonical training-state SQL fan-in and `resolve_week_generation_runtime_inputs` wiring through `_prepare_plan_generation_runtime`

Current best next seam:

1. Inspect `apps/api/app/routers/plan.py` for remaining meaningful router-local deterministic logic around `plan_generate_week` and adjacent apply/review overlay plumbing.
2. Only extract a seam if it removes real router-owned normalization or decision-prep, not if it merely relocates SQL.
3. If `plan.py` is reduced to legitimate orchestration, inspect `profile.py` and `workout.py` again for the next smallest high-value slice.

Recommended workflow:

1. Read the docs and implementation files listed above.
2. Identify one remaining meaningful seam.
3. Prefer extending an existing core-engine helper over creating a parallel abstraction.
4. Make the smallest code change that removes the router-owned deterministic behavior.
5. Run focused engine and/or API tests tied to that seam.
6. If the boundary meaningfully changes, update:
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
5. Name the next likely seam.
