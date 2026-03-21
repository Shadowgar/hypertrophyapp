# Next Actions

Last updated: 2026-03-21

This is the short execution rail for the active milestone only: `Generated Full Body Runtime Integration`.

## Ordered Steps

1. Update the active milestone docs first.
2. Create `apps/api/app/generated_full_body_runtime_adapter.py`.
3. Update `apps/api/app/routers/plan.py` to call the adapter only at the canonical full-body compatibility seam.
4. Preserve outward compatibility by forcing the scheduler-facing `program_template["id"]` to the selected compatibility template id when generated content is used.
5. Add additive runtime trace fields that separate compatibility identity from content origin and include:
   - `generated_constructor_applied`
   - stable `fallback_reason`
6. Update `packages/core-engine/core_engine/decision_generated_week.py` reason-summary and trace wording to reflect constructor-vs-fallback origin.
7. Add `apps/api/tests/test_generated_full_body_runtime_integration.py`.
8. Rewrite canonical generated-path assertions in:
   - `apps/api/tests/test_program_catalog_and_selection.py`
   - `apps/api/tests/test_phase1_canonical_path_smoke.py`
   - `apps/api/tests/test_workout_session_state.py`
9. Update `packages/core-engine/tests/test_generation.py`.
10. Run focused route and core-engine tests first, then the regression suite.

## Verification Commands

- `cd apps/api && PYTHONPATH=. python3 -m pytest tests/test_generated_full_body_runtime_integration.py tests/test_program_catalog_and_selection.py tests/test_phase1_canonical_path_smoke.py tests/test_workout_session_state.py -q`
- `cd packages/core-engine && python3 -m pytest tests/test_generation.py -q`
- `scripts/reference_ingest.sh ci`
- `./scripts/deterministic_regression_validate.sh`

## Stop Conditions

- stop if the work expands beyond generated `Full Body`
- stop if the work requires router additions or DB changes
- stop if the work changes scheduler semantics instead of runtime wiring
- stop if compatibility identity and content origin become ambiguous in trace
- stop if fallback reasons become vague or non-deterministic
- stop if anti-copy safeguards weaken during runtime activation

## Out Of Scope

- `Upper/Lower`
- `PPL`
- mesocycle review
- specialization overlays
- adaptation ledger
- authored-detail parity restoration for generated `Full Body`
- permanent generated-runtime identity redesign
