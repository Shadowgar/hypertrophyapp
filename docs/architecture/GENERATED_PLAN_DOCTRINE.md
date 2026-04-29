# Generated Plan Doctrine

## Purpose

Define an app-owned, canonical doctrine layer for the generated-plan family that ingests generalizable principles from reference materials without copying copyrighted program tables.

This doctrine governs only generated plans and explicitly preserves authored templates as separate, immutable program families.

## Scope

In scope:

- generated-plan doctrine and decision rules
- generated-plan mode taxonomy
- onboarding and re-entry branching rules
- split selection logic requirements
- progression and feedback interpretation requirements
- specialization doctrine and collision constraints
- exercise metadata requirements for safe substitution and matching
- nutrition-adjacent tracking requirements for future integration
- phased implementation roadmap for future runtime work

Out of scope:

- runtime generation logic changes
- authored program template edits
- schema migrations
- nutrition engine implementation
- copying source program tables

## Non-Goals

- Replacing authored Full Body Phase 1.
- Replacing authored Full Body Phase 2.
- Merging authored and generated program families.
- Introducing runtime behavior changes in this documentation pass.

## Program Family Boundary

Three user-facing paths are permanently distinct:

1. Authored Full Body Phase 1
2. Authored Full Body Phase 2
3. Generated Plan ("make me a plan")

Constitutional rule for this doctrine: generated plans are a separate family and must not overwrite, reinterpret, or silently replace authored program templates.

## Generated Plan Modes

### Mode 1: Base Hypertrophy (default generated mode)

- Use stable exercise selections within a block to improve progression tracking.
- Change exercises only at block boundaries, for pain/equipment mismatch, or after repeated lack of progress.
- Split choice should be informed by available training days, user preference, recovery capacity, and training status.
- Progress should be judged primarily from logbook/strength trend data.
- RPE/LSRPE/RIR feedback should inform progression decisions and fatigue management.
- Warm-up doctrine: global warm-up plus exercise-specific warm-up sets.
- Substitutions must preserve intended training effect, target muscle, loading profile, and fatigue profile.

### Mode 2: Time-Constrained Hypertrophy (Essentials-style)

- Support 2 to 5 training days/week.
- Bias toward lower volume and higher effort.
- Keep sessions near 45 minutes when feasible.
- Use fewer hard sets per exercise than base mode.
- Emphasize beating the logbook on key movements.
- Allow antagonist or non-interfering supersets to preserve time.
- Disallow interference-heavy pairings that share limiting muscles (example: DB bench paired with DB shoulder press).

### Mode 3: Advanced PPL Phase Architecture (future generated mode)

- Support advanced 6x/week PPL structure.
- Periodized phase architecture:
  - Base Hypertrophy
  - Maximum Overload
  - Supercompensation / High-Volume Phase
- Hypertrophy remains primary unless user explicitly selects strength specialization emphasis.
- Gate advanced methods by training age, recovery profile, and preference:
  - feeder sets
  - dropsets
  - cluster sets
  - stretch-biased partials (bottom-half where appropriate)
  - static stretches
  - myo-reps
  - controlled acceptable cheating only when safe and explicitly intended

## Onboarding Decision Model

Required upfront branch:

- Ask whether the user trained consistently in the last 4 weeks.

Routing doctrine:

1. Complete layoff in last 4 weeks:
- Route to comeback/bridge phase before standard generated mode.

2. Partial layoff:
- Route to reduced-volume first block or shorter re-entry block.

3. Continued heavy/consistent training:
- Route to normal generated-plan mode selection.

Additional doctrine:

- Detrained users may be flagged as strong recomposition candidates for coaching context.

## Split Selection Doctrine

Split selection inputs (required):

- available days per week
- user split preference
- recovery capacity
- training status/experience
- time availability per session
- specialization target (if any)

Selection principles:

- Highest compliance likelihood beats theoretical optimality.
- Split must match recoverable weekly workload.
- Time-constrained users should get higher-density structures.
- Specialization should influence split only when fatigue budgets can support it.

## Progression Doctrine

Core progression signals:

- completed load/reps/set quality from training logbook
- RPE/LSRPE/RIR feedback
- consistency and trend across exposures

Progression rules:

- Primary objective: progressive overload with stable exercise anchors.
- Do not force frequent exercise rotation when progression remains viable.
- Trigger exercise review only after repeated stalls, pain flags, or equipment mismatch.
- Preserve technical consistency for skill-dependent lifts.

Warm-up rules:

- Require general warm-up plus exercise-specific warm-up sets before hard work.

## Specialization Doctrine

Specialization layer sits above a recoverable base plan.

Principles:

- Specialization is not volume-only inflation.
- Priority is created through:
  - exercise placement
  - frequency
  - movement specificity
  - fatigue budgeting
- Default to one primary specialization target.
- A second weak-point target is allowed only if compatibility and recovery are both acceptable.
- Do not repeat identical specialization blocks for the same lift/body part back-to-back; insert a generalized phase between repeats.

## Collision Rules

Required incompatibility/overlap checks:

- Chest + shoulders: high pressing-overlap risk.
- Back + arms: biceps-overlap risk; reduce direct biceps volume.
- Arms + back: manage elbow flexor fatigue.
- Shoulders + arms: monitor elbow/triceps/front-delt overlap.
- Bench specialization + chest/shoulder specialization: high pressing-overlap risk.
- Squat specialization + glute/leg specialization: high lower-body systemic fatigue risk.
- Forearm specialization + back specialization: grip-overlap risk.
- Glute specialization may coexist with upper-body maintenance only if lower-body fatigue budget remains acceptable.

## Strength-Skill Specialization Doctrine

Lift-specific specialization (bench/squat) is a separate doctrine branch.

Rules:

- Maintain stable lift practice and low exercise randomness.
- Judge progress via 1RM, e1RM, AMRAP progression, or comparable top-set trend.
- Require technique consistency as a first-class success metric.
- Discourage overly frequent repeats of identical strength-skill specialization blocks.

## Exercise Metadata Requirements

Generated-plan runtime must depend on expanded exercise metadata (see `EXERCISE_METADATA_MODEL.md`) for:

- substitution quality
- collision detection
- fatigue budgeting
- split-aware pairing and supersetting
- specialization compatibility checks
- advanced-technique gating

## Re-Entry / Comeback Rules

Re-entry branch requirements:

- detect detraining status from onboarding inputs
- set conservative initial volume/intensity exposures
- re-establish technical rhythm before aggressive overload
- transition to standard generated modes only after re-entry completion checks

## Nutrition-Adjacent Tracking Requirements

No nutrition engine in this phase.

Track-ready fields for future integration:

- weekly bodyweight averages
- waist measurement
- progress photos
- optional body-part measurements
- goal label:
  - fat loss
  - recomposition
  - lean gain
  - strength focus
- protein adequacy coaching field (future)

Doctrine linkage:

- deficit/surplus/maintenance should influence recovery expectation annotations and coaching context,
- but should not directly rewrite workout programming in this phase.

## Implementation Phases

- Phase 0: docs and governance only
- Phase 1: onboarding model (detraining and re-entry routing)
- Phase 2: exercise metadata expansion
- Phase 3: split selection engine
- Phase 4: base generated hypertrophy plan
- Phase 5: time-constrained essentials-style mode
- Phase 6: specialization layer
- Phase 7: advanced PPL phase architecture
- Phase 8: recomp/progress tracking integrations

## Compliance Notes

- This document is doctrine and architecture only.
- It introduces no runtime behavior changes.
- It introduces no database migrations.
- It does not copy full source program tables.

## Phase 2E Metadata Runtime Hardening

Accepted runtime state:

- metadata-v2 seam is active in generated full-body runtime
- metadata-v2 visible grouped accounting is active
- metadata-v2 scoring influence is frozen/no-op

Frozen scoring dimensions (not active):

- fatigue/recoverability
- overlap/collision
- time efficiency
- role-fit
- substitution
- skill/stability

Reactivation policy:

- re-enable one metadata scoring signal at a time
- capture before/after archetype metrics
- require floor/guardrail test pass and metadata-off fallback pass
- require authored Phase 1/2 smoke pass
- require explicit approval before proceeding to additional signals
