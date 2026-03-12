# Runtime Authority Map

## Purpose

This document defines the permanent runtime authority architecture.

It distinguishes:

- policy owners
- doctrine substrate
- execution engines
- state assemblers
- orchestrators
- presentation-only layers

This map is the runtime-specific companion to the governance constitution.

## Constitutional Role Types

### Policy Owner

A module allowed to decide coaching outcomes.

### Doctrine Substrate

A module allowed to execute compiled doctrine and shared rule logic for policy owners.

It is not allowed to become an independent business-level owner.

### Execution Engine

A module allowed to apply policy, doctrine, and constraints to produce deterministic outcomes.

Execution engines may own execution outcomes.

Execution engines may not invent doctrine.

### State Assembler

A module allowed to normalize or assemble canonical inputs without altering coaching meaning.

### Orchestrator

A module allowed to call owners, persist outputs, and return data without reinterpreting decisions.

### Presentation-Only Layer

A layer allowed to render outcomes for humans, but not to invent or alter coaching meaning.

## Policy / Execution / Presentation Map

| Module or layer | Current constitutional role | Permanent role law |
| --- | --- | --- |
| `decision_*` modules in `packages/core-engine/core_engine/` | Policy owners | Family-level coaching authority lives here. These modules own coaching meaning for their domains. |
| `rules_runtime.py` | Doctrine substrate | Shared rule-evaluation substrate used by policy owners. It executes compiled doctrine. It does not own business-level coaching outcomes. |
| `scheduler.py` | Execution engine | Owns deterministic session construction, ordering, compression mechanics, and execution of schedule transformations. It must not invent progression policy, weak-point doctrine, substitution doctrine, or deload philosophy. |
| `generation.py` | Orchestrator + state assembler | Selects canonical generation context, loads or assembles week/day source shape, prepares generation inputs, and calls downstream owners or execution engines. It must not invent doctrine or silently become a policy owner. |
| `user_state.py` | State assembler | Assembles canonical user state from persisted runtime sources. It does not decide coaching outcomes. |
| `intelligence.py` | Orchestrator only (target); mixed legacy seam (current) | It may normalize, adapt, and forward. It may not permanently own coaching meaning. |
| API routers | Orchestrators | SQL fan-in, persistence, HTTP mapping, and response validation only. No coaching policy branches. |
| Web UI | Presentation only | Renders outputs. May classify rationale, summary, and fallback. May not invent coaching rationale or change coaching outcomes. |

## Decision-Family Map

| Module | Constitutional role | Notes |
| --- | --- | --- |
| `decision_progression.py` | Policy owner | Progression, readiness, phase-transition, and SFR meaning live here. |
| `decision_weekly_review.py` | Policy owner | Weekly-review interpretation and bounded review adjustments live here. |
| `decision_program_recommendation.py` | Policy owner | Program recommendation and switch advice live here. |
| `decision_frequency_adaptation.py` | Policy owner | Frequency-adaptation policy lives here. |
| `decision_coach_preview.py` | Policy owner | Coach preview and apply family logic lives here. |
| `decision_generated_week.py` | Policy owner | Generated-week template selection, top-level week decision ownership, and authoritative generated-week trace emission live here. |
| `decision_workout_session.py` | Policy owner | Workout-session family outputs and runtime decisions live here. |
| `decision_live_workout_guidance.py` | Policy owner | Live set feedback and workout guidance policy live here. |

## Doctrine Substrate Map

| Module | Constitutional role | Notes |
| --- | --- | --- |
| `rules_runtime.py` | Doctrine substrate | Executes compiled rule logic for progression, substitution, deload, and starting-load support. |

## Execution Map

| Module | Constitutional role | Notes |
| --- | --- | --- |
| `scheduler.py` | Execution engine | Applies doctrine and constraints to authored source structure. It owns schedule execution outcomes without owning doctrinal meaning. |

## State Assembly Map

| Module | Constitutional role | Notes |
| --- | --- | --- |
| `user_state.py` | State assembler | Canonical `UserTrainingState` assembly only. |
| `generation.py` | State assembler | Generation-context assembly only. |

## Orchestration Map

| Module or layer | Constitutional role | Notes |
| --- | --- | --- |
| `generation.py` | Orchestrator | Routes canonical generation inputs into `decision_generated_week.py`, scheduler execution, and persistence/finalization helpers. |
| `intelligence.py` | Orchestrator only (target) | Compatibility and forwarding layer only. |
| API routers | Orchestrators | IO, SQL, persistence, and HTTP concerns only. |

## Presentation Map

| Layer | Constitutional role | Notes |
| --- | --- | --- |
| Web UI | Presentation only | Renders outputs and labels rationale, summary, and fallback. It may not invent rationale. |

## Execution Modules Cannot Invent Doctrine

This is a runtime law.

Execution modules are not permitted to originate doctrinal policy.

Specifically:

- `scheduler.py` may execute weak-point handling, compression, substitution application, and ordering behavior
- `scheduler.py` may not define the meaning of progression
- `scheduler.py` may not define weak-point doctrine
- `scheduler.py` may not define substitution doctrine
- `scheduler.py` may not define deload philosophy

Those meanings must come from:

- canonical artifacts
- policy-owner modules
- the doctrine substrate

## Role Integrity Rules

- Policy owners define coaching meaning.
- Doctrine substrate executes compiled rules in support of owners.
- Execution engines apply policy and constraints to produce deterministic outcomes.
- State assemblers collect and normalize canonical inputs without changing meaning.
- Orchestrators call owners, persist outputs, and return data without reinterpretation.
- Presentation layers render outputs without inventing rationale.
