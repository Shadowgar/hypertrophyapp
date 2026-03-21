# Current State

Last updated: 2026-03-21

This document describes branch reality. For active implementation work, use `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`.

## What The Repo Already Has

- deterministic build-time ingest of `/reference` into `docs/guides/*`
- authored onboarding packages under `programs/gold/*`
- canonical rules under `docs/rules/*`
- authored-program runtime loading through `apps/api/app/program_loader.py`
- deterministic decision modules under `packages/core-engine/core_engine/*`
- focused boundary and regression tests
- compiled knowledge foundation artifacts under `knowledge/compiled/*`
- a first-class `SourceRegistry` contract and deterministic builder
- a compiled `CanonicalExerciseLibrary` foundation bundle seeded from onboarding packages
- validated doctrine and policy bundle contracts plus curated seed files
- a runtime-safe `knowledge_loader.py` boundary that loads compiled artifacts only
- deterministic `UserAssessment`
- deterministic `GeneratedFullBodyBlueprintInput`
- a deterministic, anti-copy-safe `GeneratedFullBodyTemplateDraft` constructor
- hardened generated `Full Body` draft composition with 2/4/5-day constructible coverage in tests

## What Is Partially Complete

- the `SourceRegistry` is still a foundation-stage source map, not a fully curated source graph
- the canonical exercise library is still a deterministic foundation bundle seeded from onboarding packages, not yet a full `/reference`-derived exercise knowledge model
- doctrine and policy bundles exist and validate structurally, but they are still seed-level rather than runtime-complete coaching knowledge
- canonical outward runtime identity still depends on existing template ids for compatibility
- the live generated runtime has not yet been switched to the new constructor-backed full-body path

## What Still Uses Template-First Behavior

- non-full-body generated runtime behavior remains template-first
- program recommendation still behaves like catalog selection, not true generation

## What Still Depends On Loader Inference Or Legacy Fallback

- `apps/api/app/program_loader.py` still infers some exercise metadata
- Phase 1 canonical rules still rely on a legacy scheduler overlay fallback when canonical scheduler blocks are absent
- live runtime consumers still do not broadly use the new canonical source registry or exercise library bundles directly outside the generated full-body path

## Milestone Status

- Completed milestone: `Compiled Knowledge Foundation`
- Completed milestone: `Diagnostics And Full Body Blueprint Inputs`
- Completed milestone: `Generated Full Body Template Constructor`
- Completed milestone: `Generated Full Body Constructor Hardening + Doctrine Coverage Expansion`
- Active milestone: `Generated Full Body Runtime Integration`
- Active milestone result target:
  - guarded live runtime use of the generated `Full Body` constructor
  - preserved top-level response compatibility
  - explicit separation of compatibility identity from actual content origin
  - deterministic fallback to the selected template-backed path when generation cannot be used

## Important Baseline

The active milestone assumes these systems already exist and should be treated as the integration baseline:

- `apps/api/app/knowledge_loader.py`
- `apps/api/app/generated_assessment_builder.py`
- `apps/api/app/generated_full_body_blueprint_builder.py`
- `apps/api/app/generated_full_body_template_constructor.py`
- `knowledge/compiled/doctrine_bundles/multi_source_hypertrophy_v1.bundle.json`
- `knowledge/compiled/policy_bundles/system_coaching_policy_v1.bundle.json`
- `knowledge/compiled/exercise_library.foundation.v1.json`

## Current Runtime Integration Gap

- `/plan/generate-week` still feeds an authored template directly into the scheduler
- the generated `Full Body` constructor is still library-only and test-only
- runtime trace does not yet clearly distinguish compatibility identity from actual content origin
- canonical `program_template_id` continuity must be preserved for workout history, training state, and frequency adaptation

## Intentionally Deferred

- any runtime integration beyond generated `Full Body`
- any replacement of non-full-body generated behavior
- DB model or migration work
- mesocycle review
- specialization overlays
- adaptation ledger
- transparency UI and product explanations
- broader core-engine behavior changes

## Current Live Behavior

- the assessment, blueprint, constructor, and hardening layers are complete
- live runtime integration is the current milestone
- generated `Full Body` content will be introduced only through the current canonical compatibility seam
- non-full-body runtime behavior remains template-first during this milestone
- canonical outward identity must remain stable even when live full-body content becomes generated

## Do Not Modify In This Milestone

- all routers except `apps/api/app/routers/plan.py`
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- `packages/core-engine/core_engine/*` except additive trace wording in `decision_generated_week.py`
- existing authored-program catalog, loading, and workout behavior outside the guarded full-body runtime seam
