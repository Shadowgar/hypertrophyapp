# Current State

Last updated: 2026-03-20

This document describes branch reality. The most recently completed milestone is `Compiled Knowledge Foundation`. Do not treat a new milestone as active until it is explicitly approved.

## What The Repo Already Has

- deterministic build-time ingest of `/reference` into `docs/guides/*`
- authored onboarding packages under `programs/gold/*`
- canonical rules under `docs/rules/*`
- authored-program runtime loading through `apps/api/app/program_loader.py`
- deterministic decision modules under `packages/core-engine/core_engine/*`
- active authored full-body administration paths
- focused boundary and regression tests
- additive compiled-knowledge foundation files under `knowledge/compiled/*`
- a first-class `SourceRegistry` contract and deterministic builder
- a compiled `CanonicalExerciseLibrary` foundation bundle seeded from onboarding packages
- sparse but valid doctrine and policy bundle contracts and curated seed files
- a runtime-safe `knowledge_loader.py` boundary that loads compiled artifacts only

## What Is Partially Complete

- the `SourceRegistry` is seeded from guide-ingest artifacts plus manual overrides, but it is not yet a fully curated source graph
- the canonical exercise library is a foundation-stage bundle seeded from onboarding packages, not yet a full `/reference`-derived exercise knowledge model
- doctrine and policy bundles exist as validated contracts, but they are still sparse seed bundles rather than operational runtime knowledge
- the runtime-safe loader boundary exists, but current authored and generated planning logic has not been migrated to consume the new compiled bundles yet

## What Still Uses Template-First Behavior

- generated-week planning still selects and adapts templates rather than constructing a plan from compiled doctrine
- program recommendation still behaves like catalog selection, not true generation

## What Still Depends On Loader Inference Or Legacy Fallback

- `apps/api/app/program_loader.py` still infers some exercise metadata
- Phase 1 canonical rules still rely on a legacy scheduler overlay fallback when canonical scheduler blocks are absent
- runtime consumers still do not use the new canonical source-registry or exercise-library bundles yet

## Milestone Status

- Most recently completed milestone: `Compiled Knowledge Foundation`
- Status: complete
- Result:
  - additive contracts, builders, loaders, scripts, tests, and compiled artifacts are now in place
  - runtime-safe compiled-artifact loading exists
  - compiled bundles are reproducible and verified
- There is no new active milestone yet in this document. The next milestone must be explicitly approved before implementation begins.

## Intentionally Deferred

- generated-program construction
- diagnostics and assessment runtime
- user-class runtime logic
- outcome model
- mesocycle review
- specialization overlays
- transparency UI and product explanations
- router, DB, and core-engine behavior changes

## What Should Happen Next

- Only milestone-closeout audits, deterministic hardening, or documentation clarification should happen without new approval.
- The next implementation step should move generated behavior toward true generated `Full Body` v1 using the compiled foundation, but it is not active yet.

## Do Not Modify In This Milestone

- `apps/api/app/routers/*`
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- behavior in `packages/core-engine/core_engine/*`
- existing authored-program catalog, loading, and workout behavior
