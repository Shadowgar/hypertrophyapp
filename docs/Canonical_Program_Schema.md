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
- `generated_week_scheduler_rules`
- `rationale_templates`

### `generated_week_scheduler_rules`

Canonical scheduler doctrine for generated-week execution on the adaptive gold path.

- `mesocycle`
  - `sequence_completion_phase_transition_reason`
  - `post_authored_sequence_behavior`
  - optional `soreness_deload_trigger`
  - optional `adherence_deload_trigger`
  - optional `stimulus_fatigue_deload_trigger`
- `exercise_adjustment`
  - ordered `policies[]` with explicit `match_policy`, conditions, and adjustments
  - `default_adjustment`
  - `substitution_pressure_guidance`
- `session_selection`
  - `recent_history_exercise_limit`
  - `anchor_first_session_when_day_roles_present`
  - `required_day_roles_when_compressed`
  - `structural_slot_role_priority`
  - `day_role_priority`
  - `missed_day_policy`
- `session_exercise_cap`
  - `time_budget_thresholds[]`
  - `default_slot_role_priority`
  - optional `day_role_slot_role_priority_overrides`

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
