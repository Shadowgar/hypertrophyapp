# Pure Bodybuilding Full-Body Intent Contract

## Scope
- Programs covered: `pure_bodybuilding_phase_1_full_body`, `pure_bodybuilding_phase_2_full_body`.
- Runtime objective: preserve authored multi-week intent (week/block semantics), not static session cloning.

## PDF-Derived Runtime Intent
- **Phase 1 (weeks 1-10):**
  - Weeks 1-2 are adaptation weeks (lower RPE/technique density to ramp into high frequency).
  - Weeks 3-5 are accumulation under Block 1.
  - Week 6 is a meaningful block transition into Block 2 novelty.
  - Weeks 6-10 run with higher intensity and evolved exercise exposure.
- **Phase 2 (weeks 1-10):**
  - Two 5-week blocks.
  - Week 1 is intro/deload for Block 1.
  - Week 6 is intro/deload for Block 2 and is treated as a first-class checkpoint.
  - Weeks 2-5 and 7-10 are intensification weeks.
- **Both programs:**
  - Early-set vs last-set intent must remain visible in authored execution fields.
  - Weak-point work remains bounded and intentional; compression cannot erase weak-point intent by default.
  - Progression state is user-state, while authored week identity is template-state.

## Runtime Acceptance Checklist
- Week generation yields deterministic `mesocycle.authored_week_index` and `mesocycle.authored_week_role`.
- Week 5 -> 6 transition is trace-visible and deload-active for Phase 2.
- Phase 1 week identity behavior remains unchanged.
- Authoring identity and user progression state remain decoupled in traces and behavior.
- Time-budget, substitution, and weak-point rules remain bounded when week context changes.
