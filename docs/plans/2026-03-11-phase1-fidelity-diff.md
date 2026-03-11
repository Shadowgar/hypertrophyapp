# Phase 1 Fidelity Diff

Last updated: 2026-03-11
Status: Working audit for the current source-reconciliation wave

## Purpose

Compare the current adaptive-gold runtime path against the actual Phase 1 full-body workbook/PDF doctrine so the next code wave improves the right source artifact.

Primary references:
- `reference/Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx`
- `reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf`
- `reference/Hypertrophy Handbook (Jeff Nippard) (z-library.sk, 1lib.sk, z-lib.sk).pdf`
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
- `programs/gold/adaptive_full_body_gold_v0_1.json`

## High-Level Verdict

The key architectural gap is no longer day-count compression.

That gap is now fixed enough to be useful:
- runtime starts from a real authored five-day source
- `day_role` survives the loader boundary
- scheduler compresses from five authored days down to 4/3/2 when needed
- weak-point day and primary compounds survive constrained compression much better than before

The current highest-value mismatch is now source doctrine fidelity:
- the live runtime still uses a materially different Week 1 / Week 2 exercise lineup than the actual workbook
- the first two weeks are adaptation weeks in the workbook/PDF, but that distinction is still under-modeled in the source artifacts
- the workbook’s Early Set / Last Set effort structure and last-set intensity techniques are still mostly flattened in the runtime-safe representation

## What Is Already Aligned

The current adaptive-gold path now matches the workbook/PDF on:
- 10-week mesocycle length
- 5-day authored week shape
- dedicated `Arms & Weak Points` day as a first-class day
- explicit authored deload week
- explicit post-sequence transition state
- deterministic downward compression from authored truth instead of authored-as-compressed-truth

This is an important correction. We are now improving a structurally credible full-body runtime path instead of a three-day surrogate.

## Actual Workbook/PDF Doctrine Confirmed

Confirmed from the workbook/PDF pair:
- first 2 weeks are lower-intensity adaptation weeks for the higher training frequency
- most sets in weeks 1-2 live around `~7-8` or `~8-9` RPE instead of the later `9-10` push
- working sets are explicitly split into `Early Sets` and `Last Set`
- the `Arms & Weak Points` day is not optional fluff; it is a real doctrinal day
- substitutions are authored as part of the program, not a runtime afterthought
- last-set intensity techniques are exercise-specific and vary across weeks

Confirmed from the handbook:
- Early Sets generally stop shy of failure while the Last Set often goes to failure
- RDL-family work intentionally stays farther from failure because of recovery cost
- the weak-point day can be skipped only as an explicit frequency concession, not because it is low-value by default
- if no obvious weak point is known, shoulders are the default weak-point recommendation

## Workbook Week 1 vs Current Runtime Week 1

### Workbook Week 1 - Full Body #1
Workbook:
- `Cross-Body Lat Pull-Around`
- `Low Incline Smith Machine Press`
- `Machine Hip Adduction`
- `Leg Press`
- `Lying Paused Rope Face Pull`
- `Cable Crunch`

Current runtime:
- `lat_pulldown_wide`
- `bench_press_barbell`
- `hack_squat`
- `lateral_raise_cable`
- `cable_crunch`

Gap:
- lats, chest, quad/adductor, rear-delt, and abs intent are present
- but exercise selection is materially different
- the current runtime is closer to a simplified bodybuilding day than the actual workbook day

### Workbook Week 1 - Full Body #2
Workbook:
- `Seated DB Shoulder Press`
- `Paused Barbell RDL`
- `Chest-Supported Machine Row`
- `Hammer Preacher Curl`
- `Cuffed Behind-The-Back Lateral Raise`
- `Overhead Cable Triceps Extension (Bar)`

Current runtime:
- `romanian_deadlift`
- `incline_dumbbell_press`
- `row_chest_supported`
- `leg_curl_seated`

Gap:
- the workbook day is shoulder/hamstring/row/arm focused
- the current runtime day is still much closer to the older simplified onboarding package than the actual workbook lineup
- this is one of the highest-value day-level mismatches to fix next

### Workbook Week 1 - Full Body #3
Workbook:
- `Assisted Pull-Up`
- `Paused Assisted Dip`
- `Seated Leg Curl`
- `Leg Extension`
- `Cable Paused Shrug-In`
- `Roman Chair Leg Raise`

Current runtime:
- `pullup_assisted_neutral`
- `overhead_press_seated_db`
- `split_squat_db`
- `triceps_pushdown_rope`

Gap:
- vertical pull intent survives, but the rest of the day diverges heavily
- workbook uses a tighter superset-driven, lower-rest, pull/push/hamstring/quad/trap/abs structure
- runtime currently loses that feel entirely

### Workbook Week 1 - Full Body #4
Workbook:
- `Lying Leg Curl`
- `Hack Squat`
- `Bent-Over Cable Pec Flye`
- `Neutral-Grip Lat Pulldown`
- `Leg Press Calf Press`
- `Cable Reverse Flye (Mechanical Dropset)`

Current runtime:
- `hack_squat`
- `row_machine_chest_supported`
- `dumbbell_curl_incline`
- `calf_raise_seated`

Gap:
- the current runtime keeps only part of the lower-body and calf intent
- workbook includes chest, lats, and rear-delt mechanical dropset work that runtime does not currently preserve

### Workbook Week 1 - Arms & Weak Points
Workbook:
- `Weak Point Exercise 1`
- `Weak Point Exercise 2 (optional)`
- `Bayesian Cable Curl`
- `Triceps Pressdown (Bar)`
- `Bottom-2/3 Constant Tension Preacher Curl`
- `Cable Triceps Kickback`
- `Standing Calf Raise`

Current runtime:
- `weak_chest_cable_fly`
- `weak_ham_leg_curl`
- `dumbbell_curl_incline`
- `triceps_pushdown_rope`

Gap:
- runtime preserves the weak-point day concept, which is important
- but it underrepresents the authored arm-day depth and currently hardcodes weak-point selections instead of presenting the authored weak-point slot structure

## Workbook Week 2 vs Current Runtime Week 2

Week 2 in the workbook is not just a rep-range tweak.
It keeps the same five-day structure but changes intensity-technique usage and specific exercise selection details.

Concrete week-2 workbook examples:
- `Cuffed Behind-The-Back Lateral Raise` uses `Myo-reps`
- `Overhead Cable Triceps Extension (Bar)` uses a `Dropset`
- the first two weeks still live in the adaptation RPE band instead of later-phase near-failure work

Current runtime week 2:
- does preserve a distinct authored week instead of silently repeating week 1
- but still does not preserve the actual workbook exercise lineup or the richer intensity-technique semantics

## Exercise-Library Gaps Relative To The Workbook

The workbook prominently uses exercises that are still missing or under-modeled in the current gold source path, including:
- `cross_body_lat_pull_around`
- `low_incline_smith_machine_press`
- `machine_hip_adduction`
- `leg_press`
- `lying_paused_rope_face_pull`
- `seated_db_shoulder_press`
- `paused_barbell_rdl`
- `chest_supported_machine_row`
- `hammer_preacher_curl`
- `cuffed_behind_the_back_lateral_raise`
- `assisted_pull_up`
- `paused_assisted_dip`
- `cable_paused_shrug_in`
- `roman_chair_leg_raise`
- `bent_over_cable_pec_flye`
- `neutral_grip_lat_pulldown`
- `leg_press_calf_press`
- `cable_reverse_flye`
- `bayesian_cable_curl`
- `triceps_pressdown_bar`
- `constant_tension_preacher_curl`
- `cable_triceps_kickback`
- `standing_calf_raise`

These are not small cosmetic differences. They change how the block feels in the gym.

## Semantic Gaps Still Open

### 1. Adaptation-week semantics
Current runtime still treats weeks 1-5 broadly as `accumulation`.
Source doctrine says weeks 1-2 are specifically adaptation weeks.

Missing runtime semantics:
- adaptation-specific week role or subtype
- explicit lower-intensity effort modeling for weeks 1-2
- reduced intensity-technique usage in weeks 1-2

### 2. Early Set / Last Set structure
Current runtime still flattens most exercises into one work-set prescription shape.
Source doctrine uses:
- Early Set RPE
- Last Set RPE
- Last-Set Intensity Technique

This is a major fidelity gap.

### 3. Weak-point day structure
Current runtime preserves the day but not its authored slot structure.
Source doctrine expects:
- 1 mandatory weak-point slot
- 1 optional weak-point slot
- multiple authored arm isolations
- calf work on the day

### 4. Real workbook exercise lineup
Current runtime still uses many simplified or older gold-sample exercise choices instead of the real workbook lineup.

## Most Important Gap To Fix Next

The next highest-value fix is no longer structural day count.
It is this:

- the source workbook now parses cleanly into 10 weeks / 5 authored days / real Phase 1 exercise ids
- key exercise metadata quality is now materially better at the importer boundary:
  - `leg_press` now resolves to `squat` with quad/glute emphasis
  - `seated_db_shoulder_press` now resolves to `vertical_press`
  - `triceps_pressdown_bar` now resolves to `triceps_extension`
  - `bayesian_cable_curl` now resolves to `curl`
- the loader can now flatten a source-backed multi-phase adaptive bundle into one authored runtime sequence instead of stopping after the first phase

The next remaining gap is therefore the live artifact migration itself:
- move `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` and `programs/gold/adaptive_full_body_gold_v0_1.json` from the older simplified exercise set toward the repaired source-backed workbook output
- preserve runtime semantics already proven valuable (`day_role`, `slot_role`, bounded compression, weak-point preservation, authored sequence state)

**replace the current Week 1 / Week 2 exercise lineup in the onboarding/runtime gold path with the actual workbook-backed lineup and preserve the first-two-weeks adaptation semantics while doing it.**

## Immediate Coding Implications

1. update the gold onboarding package exercise library with the real Week 1 / Week 2 workbook exercises and authored substitution options
2. update the adaptive-gold runtime artifact so Week 1 / Week 2 actually follow the workbook day structure
3. add source-backed week-1/week-2 loader/API tests before changing runtime code
4. add adaptation-week semantics for the first two weeks in a runtime-safe way
5. keep scheduler compression logic deterministic, but drive it from the corrected authored source instead of the older simplified lineup
