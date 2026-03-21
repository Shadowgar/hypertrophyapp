# Current Milestone Plan: Generated Full Body Runtime Integration

Last updated: 2026-03-21

This is the active implementation authority. If it conflicts with broader roadmap material, this document wins for current coding order.

Status: active on 2026-03-21.

## Goal

Integrate the deterministic generated `Full Body` path into the live `/plan/generate-week` runtime in a guarded, fallback-safe way while preserving:

- the current top-level response contract
- deterministic behavior
- explicit traceability
- anti-copy safeguards
- Full Body-only scope

## Scope

- add a live runtime adapter for generated `Full Body`
- activate it only on the current canonical full-body compatibility seam
- preserve canonical outward `program_template_id` and session-id continuity
- make compatibility identity and actual content origin explicitly distinct in runtime trace
- preserve deterministic fallback to the currently selected template-backed runtime path
- keep response compatibility unless authored-only exercise-detail parity is no longer structurally valid

## Baseline Dependencies

This milestone assumes these systems already exist and are the baseline for integration:

- `apps/api/app/knowledge_loader.py`
- `apps/api/app/generated_assessment_builder.py`
- `apps/api/app/generated_full_body_blueprint_builder.py`
- `apps/api/app/generated_full_body_template_constructor.py`
- `knowledge/compiled/doctrine_bundles/multi_source_hypertrophy_v1.bundle.json`
- `knowledge/compiled/policy_bundles/system_coaching_policy_v1.bundle.json`
- `knowledge/compiled/exercise_library.foundation.v1.json`
- `apps/api/app/routers/plan.py`
- `packages/core-engine/core_engine/decision_generated_week.py`

## Locked Boundaries

- Full Body only
- no `Upper/Lower`
- no `PPL`
- no router additions
- no DB model changes
- no migrations
- no persistence changes
- no mesocycle review
- no specialization overlays
- no adaptation ledger work
- no LLM runtime usage
- no architecture reopening

## Locked Compatibility Rules

- `pure_bodybuilding_phase_1_full_body` is used only as the current runtime compatibility seam.
- It is not the conceptual long-term identity model of generated `Full Body`.
- Generated runtime content must remain clearly modeled as generated in trace, even when outward compatibility preserves the canonical template id.
- Compatibility identity and actual content origin must be impossible to confuse in runtime trace or tests.
- `generated_constructor_applied: true | false` is required as an additive stable debugging/test marker.
- `fallback_reason` must be a stable stage-specific value, not freeform text.

Allowed `fallback_reason` values:

- `bundle_load_failed`
- `assessment_validation_failed`
- `blueprint_validation_failed`
- `constructor_insufficient`
- `draft_adaptation_failed`
- `unexpected_exception`

## Locked Safeguards

- Anti-copy safeguards remain in force during runtime integration.
- Session topology, day-role sequence, movement-pattern distribution, and slot assignment must still come from doctrine plus blueprint plus constructor logic.
- No single authored weekly layout may be used as a hidden default target.
- `source_program_ids` remain exercise-level provenance or ranking signals only.
- Fallback remains deterministic and local to the already selected compatibility seam.
- No reselection, no alternate split attempt, no randomization, and no silent fallback.

## Files To Create

- `apps/api/app/generated_full_body_runtime_adapter.py`
- `apps/api/tests/test_generated_full_body_runtime_integration.py`

## Files To Update First

- `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
- `docs/CURRENT_STATE.md`
- `docs/NEXT_ACTIONS.md`
- `docs/DOCUMENTATION_STATUS.md`

## Files To Update

- `apps/api/app/routers/plan.py`
- `packages/core-engine/core_engine/decision_generated_week.py`
- `apps/api/tests/test_program_catalog_and_selection.py`
- `apps/api/tests/test_phase1_canonical_path_smoke.py`
- `apps/api/tests/test_workout_session_state.py`
- `packages/core-engine/tests/test_generation.py`

## Exact Integration Seam

Activate generated runtime only when:

- `selected_template_id == "pure_bodybuilding_phase_1_full_body"`

This is a compatibility seam only. It must not be treated as the permanent generated-runtime identity model.

The route seam is:

1. after `prepare_generation_template_runtime(...)`
2. after `_prepare_plan_generation_runtime(...)`
3. before `prepare_generate_week_scheduler_runtime(...)`

## Runtime Adapter Responsibilities

The new runtime adapter must:

1. build `ProfileAssessmentInput` from existing user/profile fields
2. reuse `generation_context["training_state"]`
3. load compiled doctrine, policy, and exercise library bundles
4. build:
   - `UserAssessment`
   - `GeneratedFullBodyBlueprintInput`
   - `GeneratedFullBodyTemplateDraft`
5. convert a ready draft into a scheduler-compatible `program_template`
6. preserve outward compatibility by forcing `program_template["id"] = selected_template_id`
7. return:
   - `status`
   - `program_template`
   - `generated_full_body_runtime_trace`

## Runtime Trace Contract

Additive nested trace location:

- `template_selection_trace["generated_full_body_runtime_trace"]`

Required compatibility identity fields:

- `compatibility_selected_template_id`
- `compatibility_program_template_id`
- `compatibility_mode: "canonical_template_id_preserved"`

Required actual content origin fields:

- `content_origin: "generated_constructor_applied" | "fallback_to_selected_template"`
- `generated_constructor_applied: true | false`
- `generated_assessment_id` when applicable
- `generated_blueprint_input_id` when applicable
- `generated_template_draft_id` when applicable
- `constructibility_status` when applicable
- `fallback_reason` when applicable

Required activation/debug fields:

- `activation_guard_matched: true | false`
- `selected_template_id`
- `anti_copy_guard_mode: "doctrine_blueprint_constructor_only"`

## Exercise-Field Compatibility Contract

The live generated `Full Body` path must still guarantee these exercise fields for downstream workout, today, and logging flows:

- `id`
- `name`
- `sets`
- `rep_range`
- `recommended_working_weight`
- `movement_pattern`
- `primary_muscles`
- `primary_exercise_id`
- `substitution_candidates`

`load_semantics` may remain optional if downstream behavior continues to tolerate omission.

These authored-only fields are no longer guaranteed on the live generated `Full Body` path:

- `last_set_intensity_technique`
- `warm_up_sets`
- `working_sets`
- `early_set_rpe`
- `last_set_rpe`
- `rest`
- `substitution_option_1`
- `substitution_option_2`
- `demo_url`
- `video_url`
- `notes`
- authored video metadata objects

## Tests

- add route-level generated runtime integration coverage
- verify constructor-applied path on the canonical compatibility seam
- verify deterministic fallback with stable `fallback_reason` values
- verify non-full-body runtime behavior remains unchanged
- rewrite canonical generated-path assertions so they check:
  - stable outward identity
  - explicit content origin
  - additive `generated_constructor_applied`
  - minimum exercise-field contract
- keep workout continuity, set logging, training-state continuity, and frequency-adaptation compatibility green

## Acceptance Criteria

- `/plan/generate-week` uses the generated constructor only on the current canonical full-body compatibility seam
- live response shape remains compatible
- outward canonical `program_template_id` and session-id continuity are preserved
- compatibility identity and actual content origin are clearly separated in runtime trace
- `generated_constructor_applied` is present and stable
- fallback remains deterministic and uses only the allowed `fallback_reason` values
- minimum exercise-field compatibility is preserved for workout/today/logging flows
- anti-copy safeguards still pass
- non-full-body runtime behavior remains unchanged

## Non-Goals

- no `Upper/Lower`
- no `PPL`
- no mesocycle review
- no specialization overlays
- no adaptation ledger
- no DB changes or migrations
- no new API endpoints
- no authored-detail parity restoration for generated `Full Body`
- no new prescription engine

## Implementation Order

1. Update the active milestone docs.
2. Create `apps/api/app/generated_full_body_runtime_adapter.py`.
3. Update `apps/api/app/routers/plan.py` to call the adapter only at the canonical full-body compatibility seam.
4. Preserve outward compatibility by forcing the scheduler-facing `program_template["id"]` to the selected compatibility template id when generated content is used.
5. Add additive runtime trace fields that separate compatibility identity from content origin and include:
   - `generated_constructor_applied`
   - stable `fallback_reason`
6. Update `packages/core-engine/core_engine/decision_generated_week.py` reason-summary and trace wording to reflect constructor-vs-fallback origin.
7. Add route-level runtime integration tests.
8. Rewrite canonical generated-path assertions in API and core-engine tests.
9. Run focused integration tests, then the regression suite.

## Future Escape Hatch

This milestone preserves canonical template identity only for current runtime compatibility. It does not lock the system into authored-template ids as the permanent generated-runtime identity model.
