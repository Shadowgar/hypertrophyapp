# Next Actions

Last updated: 2026-05-10

This is the short execution rail for the active milestone: `Runtime Quality Stabilization and Documentation Alignment`.

## Ordered Steps

1. Complete Phase A documentation truth sync across active authority docs.
2. Run authored-path live/browser validation for Phase 1 and Phase 2 redistribution behavior (2/3/4/5-day).
3. Define generated weekly-volume-first distribution stage ownership and handoff rules.
4. Build generated quality-lock regression pack covering:
   - role/skeleton durability
   - weekly volume caps/floors balance
   - core exposure/reporting visibility
   - today/latest-week consistency
5. Strengthen safety/ops technical guardrails for destructive DB/test actions.

## Verification Command Categories

- Generated runtime integration + quality:
  - `apps/api/tests/test_generated_full_body_template_constructor.py`
  - `apps/api/tests/test_generated_full_body_runtime_integration.py`
- Authored adaptation + continuity:
  - `apps/api/tests/test_authored_generated_path_regression.py`
  - `apps/api/tests/test_phase1_canonical_path_smoke.py`
- Catalog/selection/workout continuity non-regressions:
  - `apps/api/tests/test_program_catalog_and_selection.py`
  - `apps/api/tests/test_workout_session_state.py`
- Core-engine generation non-regressions:
  - `packages/core-engine/tests/test_generation.py`

## Stop Conditions

- stop if generated and authored logic boundaries are blurred
- stop if authored prescriptions are mutated
- stop if metadata-v2 scoring is unintentionally re-enabled
- stop if progress/regenerate guards are weakened
- stop if documentation claims exceed validated runtime behavior

## Out Of Scope

- authored program redesign
- runtime LLM integration
- schema-driven architecture rewrite
- expansion to non-full-body generated runtime families in this milestone
