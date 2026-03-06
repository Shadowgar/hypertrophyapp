# Program Onboarding Architecture - Phase 1 (Pure Bodybuilding Full Body)

Last updated: 2026-03-06

## Scope

This phase onboards one program end-to-end before scaling:
- `Pure Bodybuilding - Phase 1 Full Body`
- Default schedule: 5 training days/week
- Runtime adaptation targets: 2, 3, 4, or 5 days/week

## Revised Architecture (One Program At A Time)

1. Program onboarding package (build-time)
- Author one structured package per program.
- Include blueprint, exercise knowledge, intent, and adaptation rules.

2. Runtime program catalog (execution-time)
- Serve only stable, loadable runtime templates.
- Exclude legacy imported artifacts from runtime selection.

3. Deterministic adaptation engine (execution-time)
- Adapt from authored 5-day structure to user-selected 2/3/4/5 days.
- Preserve compounds, weak-point priorities, and weekly coverage targets.

4. User overlay (execution-time)
- Days available, temporary duration, weak areas, equipment limits, recovery state.

## Exact Schemas (Implemented)

Implemented in `apps/api/app/adaptive_schema.py`:
- `ProgramBlueprint`, `ProgramBlueprintWeekTemplate`, `ProgramBlueprintDay`, `ProgramBlueprintSlot`
- `ExerciseKnowledgeEntry`, `ExerciseAlternative`
- `ProgramIntent`
- `FrequencyAdaptationRules`, `CoverageTarget`
- `UserOverlayConstraints`, `UserWeakAreaConstraint`
- `ProgramOnboardingPackage`
- `AdaptationDecision`, `AdaptedDayPlan`, `FrequencyAdaptationWeekResult`, `FrequencyAdaptationResult`

## Gold Standard Representation (Implemented)

- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`

This package includes:
- 10-week sequence
- multi-template weekly structure
- full-body day definitions with slot roles
- exercise library with cues/substitutions/equipment/video
- intent and adaptation rules

## Frequency Adaptation Rules (Implemented)

Core logic implemented in:
- `packages/core-engine/core_engine/onboarding_adaptation.py`

Behavior:
- accepts target days `2/3/4/5`
- anchors authored days into adapted schedule
- preserves high-priority slots (`primary_compound`, `secondary_compound`, `weak_point`)
- reduces lower-priority slots first (`isolation`, `accessory`)
- applies weak-area bias (e.g., chest/hamstrings)
- emits deterministic action trace: `preserve|combine|rotate|reduce`

## Runtime API Surfaces (Implemented)

- `POST /plan/adaptation/preview`
	- Loads onboarding package by selected program id.
	- Merges request constraints with persisted user weak areas.
	- Returns deterministic adaptation preview with decision trace.

- `POST /plan/adaptation/apply`
	- Persists temporary adaptation state (`target_days`, `duration_weeks`, `weak_areas`) for the selected runtime template.
	- Validates payload against deterministic adaptation engine before persisting.

- `POST /plan/generate-week`
	- Applies active adaptation state to effective generation frequency.
	- Decrements adaptation duration by generated week and clears state after completion.

- `GET /profile` and `POST /profile`
	- Persist and return `weak_areas` overlay used by adaptation.

## Exercise Knowledge Structure (Implemented)

Stored inside the onboarding package as `exercise_library[]` entries with:
- canonical id/name + aliases
- execution instructions and coaching cues
- primary/secondary muscles
- equipment + movement pattern
- substitutions with rationale
- default video link
- slot usage rationale

## Code To Remove/Isolate

Published in:
- `docs/redesign/Architecture_Audit_Matrix.md`

Current applied runtime isolation/deprecation:
- removed runtime endpoint coupling to guide artifacts (`reference-pairs`)
- removed corresponding web client and settings dependency
- runtime catalog excludes `*_imported.json` artifacts

## Phased Roadmap (First Program Only)

1. Stabilize single-program onboarding package and adaptation behavior
- done for baseline package + tests

2. Wire onboarding package into coaching/runtime selection path
- adaptation preview and apply endpoints implemented; full progression continuity across compressed/rejoin windows still pending

3. Validate against scenario matrix
- 2/3/4/5-day schedules
- weak-area priorities (chest/hamstrings)
- temporary reduction and reintegration

4. Add progression continuity and audit traces
- preserve lift state across compressed weeks
- store rationale for every adaptation decision

5. Scale to next program only after all above are deterministic and test-covered
