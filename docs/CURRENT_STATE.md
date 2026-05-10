# Current State

Last updated: 2026-05-10

This document describes branch reality. For active implementation work, use `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`.

## What The Repo Already Has

- deterministic build-time ingest of `/reference` into `docs/guides/*`
- authored onboarding packages under `programs/gold/*`
- canonical rules under `docs/rules/*`
- authored-program runtime loading through `apps/api/app/program_loader.py`
- deterministic decision modules under `packages/core-engine/core_engine/*`
- focused boundary and regression tests
- compiled knowledge foundation artifacts under `knowledge/compiled/*`
- runtime-safe compiled knowledge loaders and schema boundaries
- deterministic generated full-body runtime flow:
  - assessment builder
  - blueprint builder
  - template constructor
  - guarded runtime adapter
- generated and authored path separation maintained in runtime and tests

## Confirmed Runtime Reality

- Generated Full Body runtime is integrated in live `/plan/generate-week` behind compatibility guardrails.
- Generated runtime remains deterministic and non-LLM at runtime.
- Runtime trace separates compatibility identity from content origin.
- Metadata-v2 scoring remains frozen/no-op at runtime.
- Non-full-body runtime behavior remains template-first.

## Generated Quality Status

Recent generated quality work has landed across constructor/runtime/test layers, including:

- session skeleton enforcement checks
- normal 3-day volume floor behavior
- core volume reporting visibility fixes
- back-dominance caps/floors and rebalancing behavior
- today/latest-week consistency checks and regressions

Status:

- generated quality lock is active and still requires ongoing hardening via integration/live validation packs.

## Authored Path Status

- Authored source prescriptions remain unchanged.
- Authored day-count adaptation now includes dose-preserving redistribution for selected days `< 5`.
- Authored 5-day mode preserves source dose via passthrough behavior.
- Authored path remains separated from generated path logic.

Status:

- authored doctrine certification is not fully closed until a complete source-vs-app parity report is finalized across the full authored sequence.

## What Is Still Partial

- `SourceRegistry` remains foundation-stage rather than a fully curated source graph.
- canonical exercise library remains a foundation bundle seeded from onboarding packages, not full `/reference`-derived exercise intelligence.
- doctrine/policy bundles are operational but still not a complete final coaching knowledge model.
- technical safety guardrails for destructive dev/test DB operations are partially hardened but still need stronger enforcement.

## Active Milestone Direction

- Current active work is runtime quality stabilization and documentation alignment, not initial runtime integration.
- Generated path remains primary active focus.
- Authored path changes are limited to parity, adaptation regression protection, and contract integrity.

## Intentionally Deferred

- runtime integration beyond generated `Full Body`
- replacement of non-full-body generated behavior
- DB model/migration expansion for this wave
- mesocycle review redesign
- specialization overlays
- adaptation ledger
- transparency UI/product explanation redesign
