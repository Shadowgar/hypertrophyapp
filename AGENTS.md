# AGENTS.md

## Purpose
This file defines mandatory context and guardrails for all AI coding agents working in this repository.

## Mandatory Read Before Sensitive Changes
Before modifying any of the following:

- generated-plan logic
- onboarding logic
- program selection
- plan generation
- progression logic
- exercise metadata/substitution/collision logic
- workout routing

you must read all documents listed in:

- `docs/context/CONTEXT_MANIFEST.yaml`

At minimum, this includes:

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

## Non-Negotiable Runtime Governance

- Authored Full Body Phase 1 and Authored Full Body Phase 2 must remain separate from generated programs.
- Generated programs must never overwrite, modify, replace, or reinterpret authored templates.
- No runtime LLM inference is allowed.
- Raw onboarding answers must be mapped into deterministic `GenerationProfile` before any generation logic consumes them.

## Implementation Expectations

For generated-plan/onboarding/progression/routing behavior changes:

- Add or update tests that cover the behavior.
- Include deterministic decision trace/logging updates where appropriate.
- Do not claim authority beyond current doctrine and runtime boundaries.

## Forbidden In These Areas

- Silent authored/generated path merging.
- Direct use of raw onboarding answers inside generation decisions.
- Introducing non-deterministic logic for core planning outcomes.
