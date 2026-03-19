# Onboarding + Engine Roadmap (Phase 1 -> ChooseForMe)

## Purpose
Make onboarding answers deterministically control the *real engine constraint inputs* that drive:
1. exercise filtering/substitution (equipment compatibility),
2. session structure limits (time budget -> exercise/session cap),
3. movement-pattern filtering (movement restrictions).

Then evolve the product from *template-first authored delivery* into a "Choose for me" loop where the engine continuously recommends and adapts programs based on the user's constraints and logged performance.

## Current Reality (What exists today)
- The engine can generate weeks from:
  - user training state constraints (equipment, session structure budget, restrictions),
  - program templates (authored weeks),
  - rule runtime decisions (substitutions, filtering, progression/adaptation).
- The Phase 1 canonical path (`pure_bodybuilding_phase_1_full_body`) is the first end-to-end administered loop.
- The onboarding flow collects constraint inputs and persists them to the profile.

## Constraint Mapping (Onboarding -> Profile -> Engine)
The goal is that every onboarding answer that represents a constraint is persisted to the profile field that the engine already consumes.

### Equipment
- Onboarding: `gym setup` step (granular equipment tag multi-select)
- Profile: `equipment_profile: string[]`
- Engine consumption:
  - equipment compatibility + substitution paths in:
    - `packages/core-engine/core_engine/equipment.py`
    - `packages/core-engine/core_engine/rules_runtime.py` (resolve equipment substitution)
    - scheduler/planning inputs in `packages/core-engine/core_engine/scheduler.py`

### Session Time Budget
- Onboarding: `duration` step (minutes)
- Profile: `session_time_budget_minutes: int | null`
- Engine consumption:
  - scheduler session/exercise cap resolution via:
    - `packages/core-engine/core_engine/rules_runtime.py` (`resolve_scheduler_session_exercise_cap`)

### Movement Restrictions
- Onboarding: `movement limitations` step (restriction category multi-select)
- Profile: `movement_restrictions: string[]`
- Engine consumption:
  - scheduler restricted movement filtering via:
    - `packages/core-engine/core_engine/scheduler.py` (`_is_restricted_movement_pattern`, `_build_planned_exercise`)

## "Choose for me" Loop (Intended Product Behavior)
The long-term UX should behave like:
1. User sets/updates constraints (equipment, time budget, restrictions, plus later tolerance levers).
2. Engine recommends program(s) based on constraints and current training state:
   - `GET /profile/program-recommendation`
3. User can apply the recommendation:
   - `POST /profile/program-switch`
4. Week generation uses the chosen program identity while preserving adaptive engine constraints:
   - `POST /plan/generate-week`
5. User logs workout performance:
   - today/log-set -> check-in/review -> history -> adaptation
6. Engine updates future prescriptions using logged performance and preserved constraint inputs.

The key principle is: *constraint inputs are first-class*, and program selection is the engine-backed consequence of those constraints.

## Phase Plan

### Phase 1 (constraints_only)
Goal: onboarding fully persists the constraint inputs used by the engine for compatibility, time cap, and restriction filtering.

Milestones for Phase 1 exit criteria:
1. Onboarding persists:
   - `equipment_profile` as granular tags matching the settings/equipment vocabulary.
   - `session_time_budget_minutes` from onboarding `duration`.
   - `movement_restrictions` from the new onboarding movement restrictions question.
2. Engine behavior changes validated:
   - Week generation reflects time budget exercise/session caps.
   - Restricted movement patterns are absent from generated weeks.

Concrete deliverables (what should be true before Phase 1 is marked done):
- Web onboarding payload includes the constraint fields.
- Week generation uses the persisted profile constraint fields (not client-side guesses).
- Tests cover both:
  - payload persistence,
  - generate-week behavior with time budget + movement restrictions.

### Phase 2 (near-failure tolerance + underutilized levers)
Goal: wire additional constraint-like inputs that the engine already stores (`near_failure_tolerance`) into progression/scheduling decision families.

**Audit result (current state):**
- `near_failure_tolerance` is persisted on `User` (`apps/api/app/models.py`), exposed in profile and training-state responses (`apps/api/app/routers/profile.py`), and included in `constraint_state` in `packages/core-engine/core_engine/user_state.py` (`_build_constraint_state`). It is passed through `intelligence.py` payload builders and into `generation.py` when building training state for decision helpers.
- It is **not** read for any conditional or calculation in:
  - `packages/core-engine/core_engine/generation.py`: only `movement_restrictions` and `session_time_budget_minutes` are read from `constraint_state` in `resolve_week_generation_runtime_inputs`; `near_failure_tolerance` is never used there.
  - `packages/core-engine/core_engine/progression.py`: progression uses rule-set values only (e.g. `increase_percent`, `reduce_after_exposures`).
  - `packages/core-engine/core_engine/rules_runtime.py`: no reference to `near_failure_tolerance`.
  - `packages/core-engine/core_engine/scheduler.py`: no reference.
  - `packages/core-engine/core_engine/decision_weekly_review.py`: intensity/weight scaling does not take tolerance into account.

**Wiring points for future implementation:**
1. **Progression weight deltas** (`packages/core-engine/core_engine/progression.py`): scale `increase_percent` or step size by tolerance (e.g. "low" → smaller jumps, "high" → larger jumps), or gate “increase” vs “hold” using tolerance as a prior.
2. **Weekly review intensity scaling** (`packages/core-engine/core_engine/decision_weekly_review.py`): pass `near_failure_tolerance` into the review pipeline and use it to clamp or bias `global_weight_scale` / `allow_positive_progression` (e.g. "low" → more conservative scaling).
3. **Week generation runtime** (`packages/core-engine/core_engine/generation.py`): include `near_failure_tolerance` in the runtime payload passed to coach-preview / review so downstream decision families can read it without re-reading the profile.
4. **RPE / intensity targets** (authored slots or scheduler): if the engine ever sets default RPE or “last set intensity” hints, use tolerance to nudge defaults (e.g. "low" → suggest RPE 7–8, "high" → allow RPE 9+).

Exit criteria:
- `near_failure_tolerance` has a confirmed consumption path beyond raw constraint state.
- The engine uses it to modify progression/rep/weight scaling heuristics in a testable way.

### Phase 3 (Choose for me MVP UI)
Goal: implement the "Choose for me" UX using existing endpoints:
- `GET /profile/program-recommendation`
- `POST /profile/program-switch`

**Implementation plan:**
1. **Onboarding flow** (`apps/web/app/onboarding/page.tsx`): After profile save and before or after initial generate-week, call `api.getProgramRecommendation()`. If the response recommends a program different from the user’s current selection, show a short “We recommend: [Program name]” with an option to “Use this program” (call `api.programSwitch({ program_id, confirm: true })`) or “Keep my choice”. Persist choice so generate-week uses `selected_program_id`.
2. **Settings** (`apps/web/app/settings/page.tsx`): Add a “Choose for me” control (e.g. in Training setup or a dedicated section) that calls `GET /profile/program-recommendation`, displays the recommended program and rationale, and offers “Apply recommendation” via `POST /profile/program-switch` with two-step confirmation (preflight `confirm: false`, then `confirm: true`). After switch, prompt user to regenerate week if desired.
3. **API** (`apps/api/app/routers/profile.py`): Endpoints already exist; ensure they return the fields the web needs (e.g. `recommended_program_id`, `rationale`, `current_program_id`). Verify `ProgramSwitchResponse` and recommendation payload match front-end expectations.
4. **Engine** (`packages/core-engine/core_engine/decision_program_recommendation.py`): No change required for MVP; current logic already selects a program from constraints and state. Optional: expose a short “reason” string for UI display.

Exit criteria:
- UI flow allows user to accept/override engine recommendations.
- Program switching results in week generation using the selected program identity.
- Onboarding/settings are integrated so constraint changes can re-trigger recommendations.

### Phase 4 (feed more authored programs)
Goal: activate a wider authored program catalog without flattening authored execution fidelity.

**Implementation plan:**
1. **Active program set** (`apps/api/app/program_loader.py`): `ACTIVE_ADMINISTERED_PROGRAM_IDS` currently contains only `pure_bodybuilding_phase_1_full_body`. To expose a second program, add its id (e.g. `upper_lower_v1` or `ppl_v1`) to this set. `list_program_templates(active_only=True)` returns only these ids; generate-week and program-recommendation already support multiple candidates.
2. **Per-program requirements:** For each new active id ensure:
   - A **runtime template** exists under `programs/` (e.g. `programs/gold/<id>.json` or `programs/<id>.json`) and is loadable by `load_program_template`. If the id is an alias, `RUNTIME_TEMPLATE_SOURCE_IDS` must map it to the template id that actually exists (e.g. Phase 1 maps to `pure_bodybuilding_phase_1_full_body`).
   - **Onboarding package** (optional but recommended for workbook-faithful detail): `programs/gold/<onboarding_id>.onboarding.json`. Map via `ONBOARDING_SOURCE_IDS` or the loader’s onboarding resolution so generate-week and today get the right authored slots.
   - **Rules:** `RULE_SOURCE_IDS` and rule-set loading must point to a valid rule set for the template.
   - **Linked/alias ids:** Update `LINKED_PROGRAM_IDS`, `ADMINISTERED_PROGRAM_ID_ALIASES`, and `RUNTIME_TEMPLATE_SOURCE_IDS` as needed so legacy or alias ids resolve to the correct template and onboarding package.
3. **Catalog and recommendation:** `PROGRAM_NAMES` and `PROGRAM_DESCRIPTIONS` already include many ids; ensure any new active id has a name and description. The decision engine’s program recommendation will then include the new program in candidates when constraints (e.g. days_available, split_preference) match.
4. **Adding the next program:** The repo has `programs/upper_lower_v1.json` and `programs/ppl_v1.json`; their `LINKED_PROGRAM_IDS` point to phase-2 sheet ids. To activate one as a second administered program, add the id to `ACTIVE_ADMINISTERED_PROGRAM_IDS`. Runtime template and rules resolve via existing `LINKED_PROGRAM_IDS` and `docs/rules/canonical` (e.g. `pure_bodybuilding_phase_2_upper_lower_sheet.rules.json`). **Done:** `upper_lower_v1` is now active. Week generation works without an onboarding package. Frequency adaptation (preview/apply) requires an onboarding package for the program; until `programs/gold/<onboarding_id>.onboarding.json` exists for that id, those endpoints return 404 for users on that program.

Exit criteria:
- Program loader supports more active templates and linked onboarding packages.
- Loader mappings exist for:
  - runtime template assets,
  - onboarding packages,
  - linking rules between recommendation/program identities and generated-week templates.

