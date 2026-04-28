# Documentation Status

Last updated: 2026-04-28

Purpose: this is the canonical documentation index for implementation work. Use it to determine reading order, authority hierarchy, and where a document belongs before adding or moving anything.

## Read Order For Future AI Work

1. `docs/DOCUMENTATION_STATUS.md`
2. `docs/DECISIONS.md`
3. `docs/AI_WORKING_RULES.md`
4. `docs/architecture/GOVERNANCE_CONSTITUTION.md`
5. `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
6. `docs/context/CONTEXT_MANIFEST.yaml`
7. `docs/architecture/GENERATED_PLAN_DOCTRINE.md`
8. `docs/architecture/EXERCISE_METADATA_MODEL.md`
9. `docs/implementation/GENERATED_PLAN_REMEDIATION_ROADMAP.md`
10. `docs/ROADMAP.md`
11. `docs/GENERATED_PROGRAM_STRATEGY.md`
12. `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
13. `docs/GENERATED_PROFILE_SCHEMA.md`
14. `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
15. `docs/NEXT_ACTIONS.md`
16. `docs/CURRENT_STATE.md`
17. `docs/VISION.md`
18. `docs/ARCHITECTURE_ROADMAP.md`
19. `docs/current_state_decision_runtime_map.md`
20. Only then read older top-level roadmap material as supporting context

## Authority Hierarchy

1. `docs/DECISIONS.md`
   This is the locked product and architecture decision log for active work.
2. `docs/AI_WORKING_RULES.md`
   This is the implementation governance baseline for deterministic generated planning.
3. Constitutional governance docs:
   - `docs/architecture/GOVERNANCE_CONSTITUTION.md`
   - `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
4. Generated-plan doctrine docs:
   - `docs/architecture/GENERATED_PLAN_DOCTRINE.md`
   - `docs/architecture/EXERCISE_METADATA_MODEL.md`
   - `docs/implementation/GENERATED_PLAN_REMEDIATION_ROADMAP.md`
5. `docs/ROADMAP.md`
   This is the active product-focus roadmap for what gets built next.
6. Generated planning doctrine docs:
   - `docs/GENERATED_PROGRAM_STRATEGY.md`
   - `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
   - `docs/GENERATED_PROFILE_SCHEMA.md`
7. `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
   This is the implementation authority for the currently active milestone, or the completion record for the most recently finished milestone when no new milestone has been approved yet.
8. `docs/NEXT_ACTIONS.md`
   This is the short execution rail for the active repo state.
9. `docs/CURRENT_STATE.md`
   This is the branch-reality summary.
10. `docs/VISION.md` and `docs/ARCHITECTURE_ROADMAP.md`
   These define the long-term destination.
11. Older top-level docs and all supporting, audit, and archive material
   Useful context only. They do not override the current milestone docs.

## Required AI Context

Before any edits to generated-plan logic, onboarding, exercise selection/substitution, progression, specialization, program selection/routing, or workout-plan generation, the following are required context:

- `docs/context/CONTEXT_MANIFEST.yaml`
- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
- `docs/architecture/GENERATED_PLAN_DOCTRINE.md`
- `docs/architecture/EXERCISE_METADATA_MODEL.md`
- `docs/implementation/GENERATED_PLAN_REMEDIATION_ROADMAP.md`
- `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
- `docs/GENERATED_PROFILE_SCHEMA.md`
- `docs/GENERATED_PROGRAM_STRATEGY.md`
- `docs/ROADMAP.md`
- `docs/AI_WORKING_RULES.md`
- `docs/DOCUMENTATION_STATUS.md`

Governance reminder:

- Authored Full Body Phase 1 and Authored Full Body Phase 2 remain separate authored program paths.
- Generated programs must never overwrite, modify, replace, or reinterpret authored templates.

## Active Authority

These are the first docs to consult for current work:

- `docs/DECISIONS.md`
- `docs/AI_WORKING_RULES.md`
- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
- `docs/context/CONTEXT_MANIFEST.yaml`
- `docs/architecture/GENERATED_PLAN_DOCTRINE.md`
- `docs/architecture/EXERCISE_METADATA_MODEL.md`
- `docs/implementation/GENERATED_PLAN_REMEDIATION_ROADMAP.md`
- `docs/ROADMAP.md`
- `docs/GENERATED_PROGRAM_STRATEGY.md`
- `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
- `docs/GENERATED_PROFILE_SCHEMA.md`
- `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
- `docs/NEXT_ACTIONS.md`
- `docs/CURRENT_STATE.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE_ROADMAP.md`

Current status (generated-path focus update):

- `Compiled Knowledge Foundation` is complete.
- `Diagnostics And Full Body Blueprint Inputs` is complete.
- `Generated Full Body Template Constructor` is complete.
- `Generated Full Body Constructor Hardening + Doctrine Coverage Expansion` is complete.
- `Generated Full Body Runtime Integration` is complete enough for active generated calibration/onboarding follow-up.
- Active focus is generated-path calibration and generated onboarding profile specification.
- Authored-path feature expansion is paused except for regressions/integrity fixes.

## Supporting Current-State

These remain useful branch-reality and runtime references:

- `docs/current_state_decision_runtime_map.md`
- `docs/Architecture.md`
- `docs/Master_Plan.md`
- `docs/ROADMAP_MASTER_DEVELOPMENT_PLAN.md`

## Supporting / Reference

These help implementation but do not grant authority on their own:

- `docs/contracts/`
- `docs/testing/`
- `docs/flows/`
- `docs/process/`
- `docs/guides/`
- `docs/plans/`
- `docs/redesign/`
- `docs/ui-parity/`
- `docs/rules/`

## Audit / Evidence

These record what was observed or validated on a pass:

- `docs/audits/`
- `docs/validation/`
- Phase 2 validation artifacts:
  - `docs/validation/phase2_fullbody_parity_matrix.md`
  - `docs/validation/phase2_fullbody_handoff.md`

Use them as evidence, not as execution instructions.

## Historical / Archive

These are preserved for context only:

- `docs/archive/ai-handoffs/`
- `docs/archive/reviews/`
- `docs/archive/historical/`
- `docs/archive/temp/`

Do not read archive first during active implementation unless a current-state or active-implementation doc explicitly sends you there.

## Top-Level `docs/` Rule

Top-level `docs/` is allowed to hold the stable product and milestone operating guide:

- `docs/DOCUMENTATION_STATUS.md`
- `docs/DECISIONS.md`
- `docs/AI_WORKING_RULES.md`
- `docs/ROADMAP.md`
- `docs/GENERATED_PROGRAM_STRATEGY.md`
- `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
- `docs/GENERATED_PROFILE_SCHEMA.md`
- `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
- `docs/NEXT_ACTIONS.md`
- `docs/CURRENT_STATE.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE_ROADMAP.md`

Current milestone note:

- The active milestone integrates the generated `Full Body` constructor into live runtime behind the current canonical compatibility seam only.
- `pure_bodybuilding_phase_1_full_body` is a temporary compatibility anchor, not the conceptual long-term generated identity.
- Runtime trace must clearly separate compatibility identity from actual content origin and include `generated_constructor_applied`.
- Stable fallback reasons are required:
  - `bundle_load_failed`
  - `assessment_validation_failed`
  - `blueprint_validation_failed`
  - `constructor_insufficient`
  - `draft_adaptation_failed`
  - `unexpected_exception`
- The milestone must preserve deterministic fallback behavior, anti-copy safeguards, and non-full-body runtime behavior.

Older docs remain useful, but they no longer govern the active milestone unless the new operating-guide docs explicitly defer to them.

## Authority Cleanup (Roadmap/State Overlap)

Active authoritative docs for generated onboarding and generated planning:

- `docs/ROADMAP.md`
- `docs/GENERATED_PROGRAM_STRATEGY.md`
- `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
- `docs/GENERATED_PROFILE_SCHEMA.md`
- `docs/AI_WORKING_RULES.md`

Context docs that are still useful but should not guide generated onboarding implementation directly:

- `docs/Master_Plan.md`
- `docs/ROADMAP_MASTER_DEVELOPMENT_PLAN.md`
- `docs/implementation/ONBOARDING_ENGINE_ROADMAP.md`
- `docs/flows/Onboarding_and_Flows.md`
- `docs/Architecture.md`

Recommended migration actions:

1. Keep the files above for historical traceability.
2. Add a one-line “historical context only” banner to each overlap file in a follow-up docs pass.
3. Route all new onboarding/generator implementation references to the new generated authority docs listed above.

## Placement Rules

- New locked product or architecture decisions belong in `docs/DECISIONS.md`.
- New current-wave implementation guidance belongs in `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md` or `docs/NEXT_ACTIONS.md`.
- New branch-reality updates belong in `docs/CURRENT_STATE.md`.
- Dated evidence belongs in `docs/audits/` or `docs/validation/`.
- AI prompts, passoff notes, and temporary runbooks belong in `docs/archive/ai-handoffs/` unless they are actively maintained execution rails.
- If a document is no longer active but still useful, archive it rather than deleting it.
