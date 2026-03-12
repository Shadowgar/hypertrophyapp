# 2026-03-11 Pass 1 Authority Audit

Scope audited only:

- `packages/core-engine/core_engine/intelligence.py`
- `packages/core-engine/core_engine/generation.py`
- `packages/core-engine/core_engine/scheduler.py`
- `packages/core-engine/core_engine/rules_runtime.py`
- `apps/api/app/routers/plan.py`
- quick spot-checks of `apps/api/app/routers/profile.py` and `apps/api/app/routers/workout.py` only because they clearly affect coaching authority surfaces

Authority used:

- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`

## Must-fail findings

### 1. Generated week still ships without a constitutionally complete authoritative `decision_trace`

Why this fails:

- `scheduler.generate_week_plan()` returns the user-facing generated week payload with sessions, deload, and mesocycle state, but no top-level authoritative `decision_trace` at all. See `packages/core-engine/core_engine/scheduler.py:807-941`.
- `intelligence.build_generated_week_plan_payload()` only appends `template_selection_trace` and `generation_runtime_trace`; it does not construct the constitution-required authoritative trace equivalent containing owner family, policy basis, reason summary, or alternative resolution. See `packages/core-engine/core_engine/intelligence.py:1702-1731`.
- `generation.prepare_generate_week_finalize_runtime()` persists and returns that fragmented payload unchanged. See `packages/core-engine/core_engine/generation.py:1266-1315`.
- `plan_generate_week()` returns that payload directly to the first-class path. See `apps/api/app/routers/plan.py:582-665`.

Constitution impact:

- Violates Trace Completeness Law for a first-class coaching output.
- Blocks promotion for the generated-week path.

### 2. `intelligence.py` still holds live coaching authority for generation template selection

Why this fails:

- `intelligence.py` actively ranks candidates, evaluates viability, and chooses the selected generation template via `order_generation_template_candidates()` and `recommend_generation_template_selection()`. See `packages/core-engine/core_engine/intelligence.py:1847-1999`.
- That choice changes what week and sessions get performed, so it is an authoritative coaching decision under the constitution.
- The runtime map says `intelligence.py` is target-role orchestrator only, not a policy owner.
- `generation.py` imports those functions from `intelligence.py` and relies on them for template choice. See `packages/core-engine/core_engine/generation.py:8-13` and `packages/core-engine/core_engine/generation.py:585-660`.

Constitution impact:

- Shadow authority remains in `intelligence.py`.
- `intelligence.py` is still not harmless orchestration only.

### 3. `generation.py` is still carrying hidden authority instead of only assembling and routing

Why this fails:

- `generation.resolve_generation_template_choice()` previews candidate templates, computes viability via `generate_week_plan()`, and makes the final selected-template decision. See `packages/core-engine/core_engine/generation.py:561-661`.
- That is not just input assembly. It is a coaching-affecting selection seam.
- `generation.prepare_generation_template_runtime()` makes this path the normal runtime entry for template selection. See `packages/core-engine/core_engine/generation.py:664-720`.

Constitution impact:

- `generation.py` is acting as more than orchestrator + state assembler.
- Template selection authority still lacks a named policy owner in this scope.

### 4. `scheduler.py` is inventing doctrine, not just executing doctrine

Why this fails:

- Mesocycle and deload behavior are partially defined inside scheduler heuristics rather than coming only from named owners or compiled doctrine:
  - `phase == "cut"` shortens trigger weeks and early deload triggers are inferred from soreness, adherence, and SFR conditions in `_compute_mesocycle_state()`. See `packages/core-engine/core_engine/scheduler.py:168-242`.
- Exercise-level recovery and substitution pressure are invented in `_resolve_exercise_recovery_pressure()`. See `packages/core-engine/core_engine/scheduler.py:262-286`.
- Session continuity and weak-point preservation rules are embedded in `_select_sessions_with_continuity()`, including mandatory preservation of the first authored day and `weak_point_arms` day. See `packages/core-engine/core_engine/scheduler.py:647-722`.
- The final payload exposes a hardcoded coaching policy string, `missed_day_policy = "roll-forward-priority-lifts"`, with no named owner seam. See `packages/core-engine/core_engine/scheduler.py:926-941`.

Constitution impact:

- Violates the runtime-map rule that execution modules may not invent weak-point doctrine, deload philosophy, or other coaching meaning.
- Creates shadow authority inside the execution engine.

### 5. `rules_runtime.py` invents fallback doctrine when canonical rule sets are absent

Why this fails:

- `resolve_adaptive_rule_runtime()` falls back to hardcoded progression, deload, and intro-week defaults when `rule_set` is missing. See `packages/core-engine/core_engine/rules_runtime.py:85-106`.
- `resolve_substitution_rule_runtime()` falls back to hardcoded substitution strategy and threshold defaults. See `packages/core-engine/core_engine/rules_runtime.py:155-174`.
- `resolve_starting_load()` falls back to hardcoded starting-load behavior. See `packages/core-engine/core_engine/rules_runtime.py:335-404`.
- The plan router explicitly allows `rule_set` to be absent by calling `resolve_optional_rule_set()` and passing the result through to generation/scheduler. See `apps/api/app/routers/plan.py:408-412`, `apps/api/app/routers/plan.py:610-614`, and `apps/api/app/routers/plan.py:627-637`.

Constitution impact:

- `rules_runtime.py` stops being pure doctrine substrate when no compiled doctrine exists.
- This is hidden doctrine ownership, even if the defaults are deterministic.

## File-by-file assessment

### `packages/core-engine/core_engine/intelligence.py`

- Actual current role: mixed legacy seam; mostly compatibility facade for several decision families, but still an active authority holder for generation template ordering/selection and generated-week payload shaping.
- Intended constitutional role: orchestrator only.
- Complies: No.
- Exact seam/blocker:
  - Active template selection authority lives here in `order_generation_template_candidates()` and `recommend_generation_template_selection()` at `packages/core-engine/core_engine/intelligence.py:1847-1999`.
  - Generated-week final payload shaping still lives here in `build_generated_week_plan_payload()` at `packages/core-engine/core_engine/intelligence.py:1702-1731`.
  - Large legacy local policy implementations still remain in-file even where exports are rebound back to `decision_*` modules at `packages/core-engine/core_engine/intelligence.py:2568-2578` and `packages/core-engine/core_engine/intelligence.py:3122-3129`, which keeps the authority boundary ambiguous and hard to audit.

### `packages/core-engine/core_engine/generation.py`

- Actual current role: state assembler and orchestrator, plus active hidden selector for generation template choice and viability.
- Intended constitutional role: orchestrator + state assembler.
- Complies: No.
- Exact seam/blocker:
  - `resolve_generation_template_choice()` and `prepare_generation_template_runtime()` perform template-selection logic instead of forwarding to a named owner. See `packages/core-engine/core_engine/generation.py:585-720`.
  - `summarize_generation_template_viability()` uses scheduler previews as selection criteria, so this file is not just assembling canonical inputs. See `packages/core-engine/core_engine/generation.py:561-582`.
  - Finalization persists non-compliant generated-week output without constructing an authoritative trace. See `packages/core-engine/core_engine/generation.py:1266-1315`.

### `packages/core-engine/core_engine/scheduler.py`

- Actual current role: execution engine plus embedded policy/doctrine for deload, recovery pressure, weak-point continuity, and missed-day handling.
- Intended constitutional role: execution engine only.
- Complies: No.
- Exact seam/blocker:
  - Deload philosophy and mesocycle doctrine inside `_compute_mesocycle_state()` at `packages/core-engine/core_engine/scheduler.py:168-242`.
  - Exercise recovery policy inside `_resolve_exercise_recovery_pressure()` at `packages/core-engine/core_engine/scheduler.py:262-286`.
  - Weak-point / continuity doctrine inside `_select_sessions_with_continuity()` at `packages/core-engine/core_engine/scheduler.py:647-722`.
  - First-class generated-week output emitted without authoritative `decision_trace` in `generate_week_plan()` at `packages/core-engine/core_engine/scheduler.py:807-941`.

### `packages/core-engine/core_engine/rules_runtime.py`

- Actual current role: doctrine substrate, but with active fallback defaults that become de facto doctrine when compiled rules are absent.
- Intended constitutional role: doctrine substrate only.
- Complies: No.
- Exact seam/blocker:
  - Hardcoded adaptive doctrine defaults in `resolve_adaptive_rule_runtime()` at `packages/core-engine/core_engine/rules_runtime.py:85-106`.
  - Hardcoded substitution doctrine defaults in `resolve_substitution_rule_runtime()` at `packages/core-engine/core_engine/rules_runtime.py:155-174`.
  - Hardcoded starting-load fallback logic in `resolve_starting_load()` at `packages/core-engine/core_engine/rules_runtime.py:335-404`.

### `apps/api/app/routers/plan.py`

- Actual current role: orchestrator for DB fan-in, route validation, persistence, and response return.
- Intended constitutional role: orchestrator only.
- Complies: Yes for direct authority ownership. No direct router-owned coaching policy branches were found in this file.
- Exact seam/blocker if not:
  - None for direct router-owned coaching logic.
  - Separate path blocker: this router still surfaces downstream non-compliant outputs, especially doctrine-optional generation and generated-week responses lacking a complete authoritative trace. See `apps/api/app/routers/plan.py:610-614` and `apps/api/app/routers/plan.py:627-665`.

## Direct answers

### Does real coaching authority still remain in `intelligence.py`?

Yes.

The strongest active seam is generation template selection. Even though several older progression and program-recommendation exports are rebound back to `decision_*` modules, `intelligence.py` still actively decides template ordering/selection for generated weeks and still shapes the final generated-week payload. That is real coaching authority, not harmless orchestration.

### Is `scheduler.py` inventing doctrine or only executing doctrine?

It is inventing doctrine.

The clearest evidence is local mesocycle/deload logic, local recovery-pressure heuristics, local weak-point continuity behavior, and a hardcoded missed-day policy string. Those are coaching meaning seams, not just neutral execution mechanics.

### Is `generation.py` still carrying hidden authority?

Yes.

It is still performing authoritative template-choice work by evaluating candidate viability and selecting the template that generation will use. That is hidden authority relative to its intended orchestrator/state-assembler role.

### Any router-owned coaching logic in scope?

In `apps/api/app/routers/plan.py`, no direct router-owned coaching logic was found.

What the router does own is route validation, DB fan-in/out, persistence, and invoking downstream runtime helpers. The route is still part of a must-fail path because it exposes downstream authority violations, but I did not find the router itself inventing coaching policy.

Quick spot-checks of `apps/api/app/routers/profile.py:275-342` and `apps/api/app/routers/workout.py:162-332` also looked orchestration-only in the inspected slices, so I am not reporting router-owned coaching logic there in this pass.

## Promotion blockers from this pass

- Generated week lacks a constitutionally complete authoritative `decision_trace`.
- `intelligence.py` still contains live generation-selection authority.
- `generation.py` still performs hidden template-selection authority.
- `scheduler.py` still invents doctrine in first-class generation.
- `rules_runtime.py` still invents fallback doctrine when compiled rule sets are absent.

## Recommended next pass

Pass 2 should stay narrow and follow the generated-week authority chain end-to-end:

- `packages/core-engine/core_engine/decision_workout_session.py`
- `packages/core-engine/core_engine/decision_progression.py`
- `packages/core-engine/core_engine/decision_weekly_review.py`
- any compiled rule artifact files actually loaded for generated week
- the generated-week response schema / UI contract that currently receives the fragmented traces
