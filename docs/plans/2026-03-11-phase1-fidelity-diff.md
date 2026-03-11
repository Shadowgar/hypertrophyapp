# Phase 1 Fidelity Diff

Last updated: 2026-03-11
Status: Working audit for fidelity-first execution wave

## Purpose

Compare the current adaptive-gold runtime path against the richer authored doctrine represented by:

- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
- `reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf`
- `reference/Hypertrophy Handbook (Jeff Nippard) (z-library.sk, 1lib.sk, z-lib.sk).pdf`

This document exists to keep the next code wave grounded in the actual Phase 1 source instead of continuing to expand a compressed approximation.

## High-Level Verdict

The current adaptive-gold runtime path is directionally aligned with the Phase 1 full-body doctrine, but it is still materially compressed relative to the real authored source.

Current runtime shape:
- `3` live sessions (`Full Body A/B/C`)
- `days_supported` starts at `[2, 3]`
- weak-point and arms logic is present, but partially collapsed into the reduced session set

Authored source shape:
- `5` training days per week
- `4` full-body sessions plus `1` dedicated `Arms & Weak Points` day
- first `2` weeks are explicitly lower-intensity adaptation weeks
- later weeks intensify
- weak-point work is its own doctrinal feature, not just extra accessory work

## Authored Week Structure

Onboarding package week templates:

- `wk_build_a`
- `wk_build_b`
- `wk_deload`
- `wk_intens_a`
- `wk_intens_b`

Each template preserves `5` authored days:

- `fb1` `Full Body #1`
- `fb2` `Full Body #2`
- `fb3` `Full Body #3`
- `fb4` `Full Body #4`
- `fb5` `Arms & Weak Points`

Current runtime gap:
- runtime loader currently emits only `3` sessions per authored week
- days `fb4` and `fb5` are not represented as standalone authored runtime sessions

## Authored 5-Day Session Structure

### Authored `wk_build_a`

- `fb1`:
  - `lat_pulldown_wide`
  - `bench_press_barbell`
  - `hack_squat`
  - `lateral_raise_cable`
- `fb2`:
  - `romanian_deadlift`
  - `incline_dumbbell_press`
  - `chest_supported_row`
  - `leg_curl_seated`
- `fb3`:
  - `pullup_assisted_neutral`
  - `overhead_press_seated_db`
  - `split_squat_db`
  - `triceps_pushdown_rope`
- `fb4`:
  - `hack_squat`
  - `row_machine_chest_supported`
  - `dumbbell_curl_incline`
  - `calf_raise_seated`
- `fb5` `Arms & Weak Points`:
  - `weak_chest_cable_fly`
  - `weak_ham_leg_curl`
  - `dumbbell_curl_incline`
  - `triceps_pushdown_rope`

### Current runtime week-1 structure

- `Full Body A`:
  - `bench_press_barbell`
  - `row_chest_supported`
  - `lat_pulldown_wide`
  - `hack_squat`
  - `cable_crunch`
  - `weak_chest_cable_fly`
- `Full Body B`:
  - `romanian_deadlift`
  - `weak_ham_leg_curl`
- `Full Body C`:
  - `dumbbell_curl_incline`
  - `triceps_pushdown_rope`

### Concrete structural gaps

1. `fb4` is missing as a standalone runtime day.
- lost:
  - second squat exposure
  - machine chest-supported row exposure
  - calf work

2. `fb5` is collapsed into mixed runtime sessions instead of remaining a dedicated day.
- weak-point and arms intent exists, but not as a clearly separate authored day

3. `fb2` and `fb3` are underrepresented.
- `incline_dumbbell_press`
- `chest_supported_row`
- `pullup_assisted_neutral`
- `overhead_press_seated_db`
- `split_squat_db`
- `leg_curl_seated`
- `lateral_raise_cable`
- `calf_raise_seated`
  are either missing or not preserved in the live runtime session set

## Slot Roles And Weak-Point Semantics

The onboarding package preserves richer slot-role semantics than the current runtime path expresses day-to-day.

Authored source uses:
- `primary_compound`
- `secondary_compound`
- `isolation`
- `weak_point`

Current runtime issues:
- slot roles survive at the exercise level for the reduced session set
- but the larger doctrinal meaning of the dedicated `Arms & Weak Points` day is lost because day-level intent is not preserved
- weak-point work is present, but runtime does not currently preserve the authored distinction between:
  - standard session accessory work
  - weak-point day work

## Intro Weeks, Intensification, And Deload Semantics

Confirmed from the source PDF:
- first `2` weeks are lower-intensity adaptation weeks for the higher training frequency
- first `2` weeks use fewer intensity techniques
- after week `2`, intensity rises and most sets are pushed closer to failure
- working sets are separated into `Early Sets` and `Last Sets`
- weak-point day behavior depends on recovery and can include optional second weak-point exercise only if recovered

Current runtime status:
- runtime preserves a `10`-week authored mesocycle
- runtime preserves generic `accumulation`, `deload`, and `intensification` week roles
- runtime does **not yet** preserve the stronger source distinction that the first two weeks are specific adaptation weeks for frequency ramp-up
- runtime does **not yet** express `Early Sets` vs `Last Sets` semantics in a user-visible or rules-visible way

## Exercise-Library Gaps

Exercises present in onboarding source but not currently represented in the live runtime week-1 session set include:

- `incline_dumbbell_press`
- `pullup_assisted_neutral`
- `overhead_press_seated_db`
- `split_squat_db`
- `lateral_raise_cable`
- `leg_curl_seated`
- `row_machine_chest_supported`
- `calf_raise_seated`

This means the current live runtime path is still missing meaningful upper-chest, vertical-pull, overhead-press, unilateral-leg, delt, hamstring-isolation, and calf doctrine from the authored source.

## Runtime Output Gaps

### Loader output gaps

Current `load_program_template("adaptive_full_body_gold_v0_1")` returns:
- `days_supported == [2, 3]`
- `3` sessions in `sessions`
- `3` sessions per authored week in `authored_weeks`

Phase 1 source implications:
- authored source truth is `5` days
- runtime should preserve that richer authored structure before compression
- constrained schedules should be derived from `5` down to `4/3/2`, not authored directly as `3`

### Scheduler output gaps

Scheduler currently adapts from the already-compressed `3`-session authored runtime.

That means:
- compression logic has less doctrine to preserve
- weak-point and arms semantics are already partially collapsed before adaptation begins
- four-day and five-day fidelity cannot be achieved from the current runtime template shape

## Most Important Gap To Fix First

The single highest-value mismatch is this:

**The live runtime path starts from a `3`-session authored week when the real Phase 1 doctrine starts from a `5`-day authored week.**

That gap should be fixed before broadening more features, because it affects:
- fidelity
- adaptation quality
- weak-point preservation
- session feel
- user trust

## Immediate Coding Implications

1. adaptive gold runtime artifact should move closer to the `5`-day authored structure
2. loader/schema should preserve richer authored week/day semantics
3. scheduler should compress from `5` days downward only when needed
4. product UI should show clearer authored block intent once the richer runtime structure exists
