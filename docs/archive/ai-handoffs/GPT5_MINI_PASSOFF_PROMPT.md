# GPT-5 Mini Passoff Prompt

Last updated: 2026-03-09

Use the prompt below verbatim or with minimal edits when handing this repository to another AI.

## Prompt

You are taking over active development on `/home/rocco/hypertrophyapp`.

Your job is to continue the deterministic adaptive hypertrophy coaching rebuild without architectural drift.

Read these files first, in this order:

1. `docs/archive/ai-handoffs/AI_CONTINUATION_GOVERNANCE.md`
2. `docs/Master_Plan.md`
3. `docs/redesign/Adaptive_Coaching_Redesign.md`
4. `docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md`
5. `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
6. `docs/audits/Master_Plan_Checkmark_Audit.md`
7. `README.md`

Then inspect these implementation files before making changes:

1. `packages/core-engine/core_engine/intelligence.py`
2. `packages/core-engine/core_engine/generation.py`
3. `packages/core-engine/core_engine/user_state.py`
4. `packages/core-engine/core_engine/rules_runtime.py`
5. `apps/api/app/adaptive_schema.py`
6. `apps/api/app/routers/plan.py`
7. `apps/api/app/routers/profile.py`
8. `apps/api/app/routers/workout.py`

Non-negotiable architecture rules:

1. Deterministic coaching logic, normalization, and payload preparation belong in `packages/core-engine`, not in API routers.
2. Routers should be limited to auth, SQL reads/writes, persistence, HTTP error mapping, and response validation.
3. Prefer canonical `UserTrainingState` whenever a decision family needs user history, adherence, soreness, fatigue, progression, or generation context.
4. Do not introduce new runtime dependence on `docs/guides/*` artifacts.
5. Do not add new coaching behavior to raw fallback paths unless necessary for backward compatibility. Fallback inputs may remain, but canonical runtime-backed paths are the priority.
6. Preserve or add structured `decision_trace` output for migrated decision families.
7. Make small slices: one meaningful seam at a time, with focused tests and doc updates.

Important repo-specific constraints:

1. Use `apps/api/.venv/bin/python` directly. Do not rely on `source apps/api/.venv/bin/activate`; it may fail or be absent.
2. Clean up temporary SQLite files created by focused API tests, such as `apps/api/test_local_*.sqlite3`.
3. Avoid unrelated cleanup or broad refactors. This repo can be noisy.
4. Do not revisit already migrated boundaries unless a failing test proves a regression.

What is already migrated and should not be re-extracted:

1. Canonical `UserTrainingState` assembly and `/profile/training-state`.
2. Program recommendation and program switch canonical user-state consumption.
3. Weekly review window/status, summary preparation, decision packaging, and submit payload shaping.
4. Coach-preview canonical training-state history/context preference.
5. Template loading and selection orchestration for coach-preview and generate-week.
6. Workout resume-state derivation, today-session selection, completed-set aggregation, today payload hydration, summary runtime preparation, log-set response payload shaping, repeat-failure substitution payload shaping, log-set planned exercise normalization, session-state default seeding, and session-state persistable payload preparation.

Latest work completed in the current branch:

1. `packages/core-engine/core_engine/intelligence.py`
   - Added `build_workout_performance_summary`.
   - Added `build_repeat_failure_substitution_payload`.
   - Added `build_workout_today_session_state_payloads`.
   - Added `resolve_workout_log_set_plan_context`.
   - Added `build_workout_session_state_defaults`.
   - Added `prepare_workout_session_state_persistence_payload`.
2. `apps/api/app/routers/workout.py`
   - Now resolves stored workout plan context once per request.
   - Now delegates substitution payload shaping, planned exercise normalization, summary prep, and session-state prep to core-engine helpers.
3. `apps/api/app/routers/plan.py`
   - `plan_generate_week` now centralizes the canonical training-state SQL fan-in and `resolve_week_generation_runtime_inputs` wiring through `_prepare_plan_generation_runtime` instead of inlining the whole read set in the route body.

Focused regressions that currently pass after the latest slices:

1. `apps/api/tests/test_workout_logset_feedback.py`
2. `apps/api/tests/test_workout_progress.py`
3. `apps/api/tests/test_workout_resume.py`
4. `apps/api/tests/test_workout_session_state.py`
5. `apps/api/tests/test_workout_summary.py`
6. `apps/api/tests/test_program_frequency_adaptation_api.py`
7. `apps/api/tests/test_program_catalog_and_selection.py`
8. `apps/api/tests/test_weekly_review.py`
9. Focused subsets in `packages/core-engine/tests/test_intelligence.py`

How to continue from here:

1. Start by inspecting `apps/api/app/routers/plan.py` for remaining meaningful router-local normalization or decision-prep around `plan_generate_week` and adjacent recommendation/apply flows.
2. Do not extract pure SQL helpers just for style. Only extract logic if it reduces router-owned deterministic behavior or repeated normalization around engine calls.
3. If `plan.py` has no worthwhile deterministic seam left beyond SQL orchestration, inspect remaining router-local wrappers in `profile.py` and `workout.py` and choose the smallest high-value slice.
4. Prefer extending an existing core-engine helper over creating a brand new parallel abstraction.
5. After each slice, run the smallest relevant focused tests first. Only run `./scripts/mini_validate.sh` after a cluster of meaningful changes or when changing a central boundary.

Validation protocol:

1. For focused API tests, run from `apps/api` with `TEST_DATABASE_URL=sqlite:///./test_local_<name>.sqlite3 apps/api/.venv/bin/python -m pytest <test file>`.
2. For focused engine tests, run from `packages/core-engine` with `apps/api/.venv/bin/python -m pytest tests/test_intelligence.py -k <pattern>`.
3. When a slice is substantial or touches shared contracts, run `./scripts/mini_validate.sh`.
4. Remove any temporary SQLite files created during focused API tests.

Documentation protocol:

1. If you move a meaningful boundary into core-engine, update:
   - `docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md`
   - `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
   - `docs/audits/Master_Plan_Checkmark_Audit.md` when the evidence summary materially changes
2. If the change is only internal router cleanup with no new architectural boundary, docs can stay unchanged unless the handoff would become misleading.

What to avoid:

1. Do not move DB access into core-engine.
2. Do not add client-only coaching heuristics in the web app when deterministic API payloads already exist.
3. Do not rewrite existing migrated helpers unless tests prove they are wrong.
4. Do not introduce broad formatting-only changes.

When you finish your first slice, report:

1. What seam you selected and why.
2. Which files changed.
3. Which focused tests passed.
4. Whether `mini_validate` was run.
5. What the next likely seam is.
