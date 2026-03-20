# Current Milestone Plan: Compiled Knowledge Foundation

Last updated: 2026-03-20

This is the active implementation authority. If it conflicts with broader roadmap material, this document wins for current coding order.

Status: completed on 2026-03-20. This document now serves as the implementation record and boundary for the finished `Compiled Knowledge Foundation` milestone until a new milestone is explicitly approved.

## Goal

Build the compiled-knowledge substrate the future generator will depend on without changing routers, DB models, authored-program behavior, or generated-program logic.

## Scope

- `ReferenceKnowledgeContract`
- `SourceRegistry`
- `SourceToKnowledgePipeline` skeleton
- `CanonicalExerciseLibrary` foundation
- doctrine bundle contract
- policy bundle contract
- stronger no-raw-reference runtime enforcement

## Canonical Source Rules

- `/reference` remains the canonical knowledge source.
- `docs/guides/*` may be used as deterministic intermediate build artifacts derived from `/reference`, but they are not canon.
- Runtime must never read raw `/reference`.
- Runtime must consume only compiled artifacts.
- For this milestone only, the canonical exercise library may be seeded from onboarding packages for determinism and low risk.
- That exercise-library approach is a foundation stage, not the final exercise knowledge model.
- Later milestones must expand exercise knowledge from `/reference` technique and specialization materials.

## Files To Create

- `apps/api/app/knowledge_schema.py`
  Pydantic contracts for source registry, provenance refs, exercise library bundle, doctrine bundle, policy bundle, manifest, hard constraints, soft preferences, minimum-viable fallback, anti-overadaptation, and data sufficiency.
- `apps/api/app/knowledge_loader.py`
  Runtime-safe compiled-artifact loaders. No raw-source fallbacks allowed.
- `importers/source_registry_builder.py`
  Deterministic source-registry builder from guide-ingest outputs plus manual overrides.
- `importers/exercise_library_foundation.py`
  Canonical exercise-library foundation builder from `programs/gold/*.onboarding.json`.
- `importers/source_to_knowledge_pipeline.py`
  Build-time orchestrator for compiled artifacts.
- `knowledge/curation/source_registry_overrides.json`
  Manual classification corrections.
- `knowledge/curation/doctrine_bundles/multi_source_hypertrophy_v1.seed.json`
  Sparse but valid doctrine seed bundle.
- `knowledge/curation/policy_bundles/system_coaching_policy_v1.seed.json`
  Sparse but valid policy seed bundle.
- `knowledge/compiled/source_registry.v1.json`
- `knowledge/compiled/exercise_library.foundation.v1.json`
- `knowledge/compiled/doctrine_bundles/multi_source_hypertrophy_v1.bundle.json`
- `knowledge/compiled/policy_bundles/system_coaching_policy_v1.bundle.json`
- `knowledge/compiled/build_manifest.v1.json`

## Files To Update

- `apps/api/app/config.py`
  Add `compiled_knowledge_dir`.
- `apps/api/Dockerfile`
  Copy `knowledge/` into the API image so containerized validation can load curated seed bundles and compiled artifacts.
- `scripts/reference_ingest.sh`
  Run the new compiled-knowledge pipeline after raw corpus ingest.
- `scripts/deterministic_regression_validate.sh`
  Include the new knowledge-contract tests.
- `docs/DOCUMENTATION_STATUS.md`
  Point future sessions to the new docs first.

## Required Contract Rules

- All compiled bundles must have stable ordering.
- All compiled bundles must carry explicit `schema_version`, `bundle_version`, `input_signature`, `output_signature`, and `aggregate_signature`.
- Clean rebuilds must be reproducible.
- Sparse doctrine and policy modules are allowed only if structurally valid and explicitly marked `seed` or `placeholder`.
- Hard constraints and soft preferences must be distinct types now.
- Minimum-viable fallback, anti-overadaptation, and data-sufficiency policies must exist as policy contracts now even though runtime will not consume them yet.

## Build Flow

1. `importers/reference_corpus_ingest.py` regenerates deterministic guide-ingest artifacts from `/reference`.
2. `importers/source_registry_builder.py` compiles the source registry from those artifacts plus overrides.
3. `importers/exercise_library_foundation.py` compiles the exercise-library foundation from onboarding packages.
4. `importers/source_to_knowledge_pipeline.py` validates doctrine and policy seed bundles, emits compiled outputs, and writes the build manifest.
5. `apps/api/app/knowledge_loader.py` becomes the runtime-safe entrypoint for compiled artifacts.

## Tests

- `apps/api/tests/test_source_registry_contract.py`
- `apps/api/tests/test_source_to_knowledge_pipeline.py`
- `apps/api/tests/test_exercise_library_contract.py`
- `apps/api/tests/test_knowledge_loader.py`
- expand `apps/api/tests/test_runtime_source_boundaries.py`
- keep `apps/api/tests/test_reference_corpus_ingestion.py` as a regression guard

## Acceptance Criteria

- `scripts/reference_ingest.sh ci` regenerates both guide-ingest artifacts and compiled knowledge artifacts deterministically.
- Every compiled artifact validates against `knowledge_schema.py`.
- Runtime can load compiled source registry, exercise library, doctrine bundle, and policy bundle through `knowledge_loader.py`.
- Runtime has no raw `/reference` access.
- Current authored/runtime behavior is unchanged.
- No router behavior changes.
- No DB migrations.
- No generated-program logic changes.

## Completion Notes

- The milestone deliverables were implemented additively.
- The compiled foundation now includes:
  - `knowledge/compiled/source_registry.v1.json`
  - `knowledge/compiled/exercise_library.foundation.v1.json`
  - `knowledge/compiled/doctrine_bundles/multi_source_hypertrophy_v1.bundle.json`
  - `knowledge/compiled/policy_bundles/system_coaching_policy_v1.bundle.json`
  - `knowledge/compiled/build_manifest.v1.json`
- Verification passed through:
  - `scripts/reference_ingest.sh ci`
  - focused milestone API tests
  - `./scripts/deterministic_regression_validate.sh`
- The doctrine and policy bundles are intentionally sparse seed bundles at this stage. They validate structurally, but they are not yet runtime-complete coaching doctrine.

## Non-Goals

- No generated-program constructor
- No diagnostics runtime
- No user-class runtime logic
- No outcome-model runtime
- No mesocycle-review runtime
- No specialization engine
- No transparency UI
- No migration of current program loader or core-engine behavior to the new bundles yet

## Do Not Touch In This Milestone

- `apps/api/app/routers/*`
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- behavior in `packages/core-engine/core_engine/*`
- existing authored-program runtime behavior
