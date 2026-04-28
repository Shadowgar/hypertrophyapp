# Exercise Metadata Model

## Purpose

Define canonical exercise metadata required for generated-plan doctrine execution, substitution integrity, collision detection, fatigue budgeting, and future specialization routing.

This model is architecture guidance for future implementation. It does not change runtime behavior in this pass.

## Required Fields

- `exercise_id`
- `display_name`
- `primary_muscles` (array)
- `secondary_muscles` (array)
- `movement_pattern`
- `joint_actions` (array)
- `equipment`
- `laterality` (`unilateral` or `bilateral`)
- `exercise_type` (`compound` or `isolation`)
- `program_role` (`primary`, `secondary`, `tertiary`)
- `fatigue_cost` (normalized tier or numeric scale)
- `axial_loading` (tier)
- `grip_demand` (tier)
- `pressing_overlap` (tier)
- `pulling_biceps_overlap` (tier)
- `triceps_overlap` (tier)
- `front_delt_overlap` (tier)
- `trap_overlap` (tier)
- `lower_back_fatigue` (tier)
- `stretch_biased` (boolean)
- `shortened_position_bias` (boolean)
- `skill_specific_lift` (boolean)
- `substitution_family`
- `contraindication_or_pain_notes`
- `time_efficiency` (tier)
- `advanced_technique_compatibility` (array of tags)

## Optional Fields

- `tempo_sensitivity`
- `setup_complexity`
- `learning_curve`
- `machine_path_stability`
- `spotter_recommended`
- `min_equipment_requirements`
- `max_loadability_profile`
- `rom_constraints`
- `common_form_breakdown_flags` (array)
- `safety_notes`
- `superset_pairing_notes`
- `last_reviewed_at`
- `doctrine_version`

## Example JSON-Like Schema

```json
{
  "exercise_id": "string",
  "display_name": "string",
  "primary_muscles": ["chest"],
  "secondary_muscles": ["front_delts", "triceps"],
  "movement_pattern": "horizontal_press",
  "joint_actions": ["shoulder_horizontal_adduction", "elbow_extension"],
  "equipment": "barbell",
  "laterality": "bilateral",
  "exercise_type": "compound",
  "program_role": "primary",
  "fatigue_cost": "medium_high",
  "axial_loading": "low",
  "grip_demand": "low",
  "pressing_overlap": "high",
  "pulling_biceps_overlap": "none",
  "triceps_overlap": "high",
  "front_delt_overlap": "high",
  "trap_overlap": "low",
  "lower_back_fatigue": "low",
  "stretch_biased": true,
  "shortened_position_bias": false,
  "skill_specific_lift": true,
  "substitution_family": "barbell_horizontal_press",
  "contraindication_or_pain_notes": "Use shoulder-friendly ROM variant if anterior shoulder pain.",
  "time_efficiency": "high",
  "advanced_technique_compatibility": ["cluster_sets", "myo_reps_limited"]
}
```

## Substitution Matching Rules

A valid substitution should preserve the original training intent across these ordered constraints:

1. `primary_muscles` match or near-match.
2. `movement_pattern` match.
3. `joint_actions` equivalence (or closest safe equivalent).
4. Similar `program_role` intent (primary stays primary when feasible).
5. Comparable loading/fatigue profile:
- `fatigue_cost`
- `axial_loading`
- `lower_back_fatigue`
6. Overlap compatibility constraints preserved:
- pressing/pulling/triceps/front-delt/trap tags.
7. Equipment feasibility for user context.
8. Pain/contraindication constraints.
9. Time-efficiency compatibility with selected mode.

Hard fails for substitution:

- introduces known pain conflict
- materially changes target muscle intent
- materially increases overlap risk in already constrained sessions
- breaks skill-specific lift stability in strength-skill blocks

## Collision-Tag Definitions

Use normalized tiers (`none`, `low`, `medium`, `high`) for overlap tags.

- `pressing_overlap`: shared pressing-limiting musculature (chest/front-delt/triceps complex).
- `pulling_biceps_overlap`: overlap in pull patterns that tax elbow flexors/biceps.
- `triceps_overlap`: elbow extension fatigue carryover and lockout-fatigue impact.
- `front_delt_overlap`: anterior deltoid loading overlap from press and raise patterns.
- `trap_overlap`: upper-trap loading overlap with pulls/carries/shrugs.
- `lower_back_fatigue`: spinal erector/systemic low-back fatigue contribution.
- `grip_demand`: forearm/grip bottleneck potential relevant to pull/specialization collisions.

Collision tags are used for:

- same-session pairing safety
- weekly overlap budgeting
- specialization compatibility checks
- time-constrained superset pair selection

## Advanced Technique Compatibility Tags

Recommended tag set:

- `feeder_sets_ok`
- `dropset_ok`
- `cluster_set_ok`
- `stretch_partial_ok`
- `static_stretch_ok`
- `myo_rep_ok`
- `controlled_cheat_ok`
- `controlled_cheat_not_recommended`

Tag usage rules:

- Compatibility tags indicate potential eligibility, not mandatory prescription.
- Final application must still be gated by user training age, recovery, mode, and stated preference.
- Skill-specific lifts should default conservative for fatigue-intensive methods unless explicitly authorized by doctrine branch.

## Governance Notes

- Metadata values must be app-owned and maintainable.
- Source references may inform tags, but direct table copying is prohibited.
- Runtime adoption occurs only in future implementation phases.
