# Canonical Program Schema - Adaptive Runtime Contract

Last updated: 2026-03-06

## Goal

Represent training programs with explicit coaching semantics and no ambiguity.

## Program Template

- `program_id`: string
- `program_name`: string
- `version`: semver string
- `source_workbook`: string path or source key
- `split`: enum (`full_body`, `upper_lower`, `ppl`, ...)
- `phases[]`

## Phase

- `phase_id`: string
- `phase_name`: string
- `intent`: string
- `weeks[]`

## Week

- `week_index`: integer
- `days[]`

## Day

- `day_id`: string
- `day_name`: string
- `slots[]`

## Slot

- `slot_id`: string
- `order_index`: integer
- `exercise_id`: canonical exercise ID
- `video_url`: optional
- `warmup_prescription[]`
- `work_sets[]`
- `notes`: optional

## Warmup Prescription Row

- `percent`: integer
- `reps`: integer
- optional `rest_seconds`

## Work Set Prescription Row

- `set_type`: enum (`work`, `top`, `backoff`)
- `sets`: integer
- `rep_target.min`: integer
- `rep_target.max`: integer
- optional `rir_target` or `rpe_target`
- optional `load_target`

## Exercise Catalog Contract

- `exercise_id`
- `canonical_name`
- `aliases[]`
- `movement_pattern`
- `primary_muscles[]`
- `secondary_muscles[]`
- `equipment_type[]`
- `default_video_url`
- `substitutions[]`

## Coaching Rules Contract

- `rule_set_id`
- `program_scope[]`
- `starting_load_rules`
- `progression_rules`
- `underperformance_rules`
- `fatigue_rules`
- `deload_rules`
- `phase_transition_rules`
- `substitution_rules`
- `rationale_templates`

## User Training State Contract

- `user_program_state`
- `exercise_performance_history`
- `progression_state_per_exercise`
- `fatigue_state`
- `adherence_state`
- `stall_state`

## Validation Rules

- Importers must fail or emit explicit ambiguity diagnostics when required fields are missing.
- Structural labels (week/block headers, rest-day labels) must never become runtime exercise slots.
