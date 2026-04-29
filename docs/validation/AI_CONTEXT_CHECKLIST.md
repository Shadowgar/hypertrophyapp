# AI Context Checklist

Last updated: 2026-04-28
Purpose: lightweight pre-flight and post-change checklist for generated-plan and onboarding work.

## Must-Read Docs Before Generated-Plan Work

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

## Forbidden Changes

- Generated plan runtime modifying/replacing/reinterpreting authored templates.
- Merging authored Full Body Phase 1 or Full Body Phase 2 into generated family logic.
- Runtime LLM inference for workout/program decisions.
- Direct use of raw onboarding answers in generation without deterministic `GenerationProfile` mapping.
- Untraced decision changes in generated-plan routing/progression/specialization.
- Re-enabling metadata-v2 scoring signals without explicit approved reactivation phase and metrics evidence.

## Metadata-v2 Hardening Gate

Current accepted state:

- metadata-v2 seam: enabled
- metadata-v2 visible grouped accounting: enabled
- metadata-v2 scoring: disabled/no-op

Future reactivation requirements:

1. one scoring signal at a time
2. before/after metrics for novice, low-time, low-recovery, weak-point arms/delts
3. guardrail floors pass (core/arms/delts nonzero when viable; major-group floors intact)
4. metadata-off fallback tests pass
5. authored Phase 1/2 smoke tests pass
6. explicit approval before next signal

## Required Tests

- Unit tests for generated-plan/onboarding decision branches changed.
- Regression tests proving authored and generated path separation is preserved.
- Tests for deterministic profile mapping when onboarding inputs change.
- Decision trace assertions where authoritative plan decisions are changed.

## Required Final Report Items

- Files changed.
- Mandatory context docs read.
- Governance constraints checked (authored/generated separation, no runtime LLM).
- Tests run and results.
- Trace/logging changes made (or explicit reason none were required).
- Residual risks and next recommended phase.
