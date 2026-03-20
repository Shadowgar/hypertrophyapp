# Phase 1 vs Phase 2 Full-Body Parity Matrix

## Scenarios
- Week identity generation: week 1, week 5, week 6, week 10.
- Week 5 -> 6 transition checkpoint semantics.
- Multi-week progression continuity and interruption/resume behavior.
- Constraint consistency across rotated weeks (time-budget and movement restrictions).

## Evidence
- `apps/api/tests/test_program_catalog_and_selection.py`
  - `test_phase2_generate_week_uses_canonical_template_and_week1_deload`
  - `test_phase2_generate_week_uses_week_five_before_transition`
  - `test_phase2_generate_week_week_five_to_six_transition_is_checkpoint`
  - `test_phase2_generate_week_supports_interruption_and_resume_and_week_ten`
  - `test_phase2_time_budget_compression_applies_across_block_transition`
  - `test_phase2_movement_restrictions_remain_enforced_on_rotated_weeks`
- `apps/api/tests/test_program_loader.py`
  - runtime alias and rules resolution tests for Phase 2 canonical ID.

## Pass/Fail
- Full-body catalog contains both canonical active programs (Phase 1 + Phase 2): **PASS**.
- Phase 2 week identity and transition checkpoint visibility in `mesocycle`: **PASS**.
- Week 5 -> 6 transition treated as first-class checkpoint (`transition_checkpoint=true` at week 6): **PASS**.
- Interruption/resume scenario preserves authored-week mapping by prior generated week count: **PASS**.
- Restriction safety on rotated weeks (`vertical_press` absent under overhead restriction): **PASS**.
- Time-budget signal preserved in runtime trace across block transition: **PASS**.

## Compression Policy Decision
- **Policy selected:** flexible, trace-first acceptance.
- **Meaning:** compression validation on active full-body paths must assert authoritative runtime signals (time-budget inputs, compression decisions, retention priorities), not a fixed per-session exercise count.
- **Rationale:** scheduler count outcomes may vary by authored week composition while still preserving intent; decision quality should be judged by deterministic policy traces and safety constraints.
- **Test standard:** keep assertions focused on trace-backed policy signals (for example `recovery_inputs.session_time_budget_minutes`) and intent-preservation checks, not hard-coded slot counts.
