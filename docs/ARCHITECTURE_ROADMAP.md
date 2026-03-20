# Architecture Roadmap

Last updated: 2026-03-20

This document is the locked architecture target. It defines the destination. For the active coding rail, use `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`.

## Locked Runtime Stack

- `/reference` doctrine
  Extracted training knowledge and authored intent.
- `SystemCoachingPolicy`
  App-authored higher-order coaching logic.
- `DecisionEngine`
  Deterministic runtime executor using compiled doctrine, policy, ontology, and user state.

## Core Architecture

- `ReferenceKnowledgeContract`
  `/reference` is the sole canonical knowledge corpus. Every compiled rule, exercise record, and explanation must trace back to it through provenance.
- `SourceToKnowledgePipeline`
  Offline ingestion, extraction, normalization, conflict detection, curation, compilation, and validation.
- `CanonicalExerciseLibrary`
  Canonical exercise and exercise-variant records tied to the ontology.
- `TrainingOntology`
  Muscles, movement patterns, exercise families, stimulus roles, fatigue, skill, stability, equipment, substitution, and overlap relations.
- `SystemCoachingPolicy`
  Explicit app-authored tradeoff logic such as adherence-first weighting, conservative behavior under uncertainty, schedule compression, and tie-break rules.
- `UserClassModel`
  Coaching-relevant classes such as novice, early intermediate, advanced, low recovery, inconsistent schedule, home-gym constrained, technique limited, specialization seeking, and comeback or detrained.
- `ConstraintResolutionPolicy`
  Deterministic resolution of conflicts such as split preference vs available days, weak-point emphasis vs recovery limits, and time budget vs variety.
- `Diagnostics and Assessment`
  Structured evaluation inputs and deterministic assessment outputs used to drive generated planning.
- `Generated Program Versioning`
  Generated plan versions, adaptation ledger, reason codes, before/after diffs, and observed-impact tracking.
- `OutcomeModel`
  Adherence, progression, recovery, fatigue burden, exposure, weak-point trend, session completion, time-budget compliance, and exercise success or replacement trends.
- `MesocycleReviewLayer`
  Deterministic block review above week-to-week adaptation.
- `TechnicalCoachingLayer`
  Deterministic setup cues, execution priorities, effort guidance, progression guidance, warnings, and swap recommendations.
- `Transparency Surfaces`
  User-facing "why this plan", "why this split", "why this exercise", "why this changed", current weak-point status, and current training priority views.
- `PromotionAndActivationGate`
  New doctrine and policy bundles activate only after provenance, schema, conflict, coverage, safety, explanation, fidelity, and curation checks pass.
- `LocalOfflineRuntimeGoal`
  Core generation, adaptation, review, and explanation should eventually run locally or offline from compiled artifacts.

## Runtime Rules

- Hard constraints and soft preferences are separate contract types.
- Hard constraints are non-negotiable blockers or filters.
- Soft preferences are weighted desires that may be dropped after feasibility checks.
- Minimum-viable-program fallback is required.
- Anti-overadaptation rules are required.
- Data sufficiency rules are required before major changes.
- Runtime always uses compiled artifacts only.

## Mode Targets

- `authored`
  Selectable authored products remain first-class for the life of the system.
- `optimized_generated`
  A true doctrine-driven coaching engine, not a template playback system.

## Generated v1

- Scope: generated `Full Body` only.
- Must use compiled artifacts only.
- Must honor hard constraints.
- Must resolve soft preferences deterministically.
- Must have minimum-viable fallback.
- Must have anti-overadaptation and data-sufficiency policy contracts.
- Must provide user-facing rationale for plan, split, exercise, and change decisions.

## Future Generated Target

- Generated `Upper/Lower`
- Generated `PPL`
- "Best split for me" selected by the engine

## Phase Order

1. Compiled Knowledge Foundation
2. Diagnostics and Assessment
3. UserClassModel and runtime policy execution
4. Generated Full Body constructor
5. OutcomeModel and adaptation ledger
6. Mesocycle review and specialization overlays
7. Technical coaching and transparency surfaces
8. Split expansion after doctrine, policy, and archetype coverage are complete
