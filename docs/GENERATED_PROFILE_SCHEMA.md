# Deterministic Generated Profile Schema

Last updated: 2026-04-27
Status: active generated-profile contract

## Purpose
Define the internal deterministic `GenerationProfile` derived from onboarding answers for generated plan construction.

## Contract

| Field | Type | Required | Allowed values / shape | Source |
|---|---|---|---|---|
| `goal_mode` | enum | yes | `hypertrophy`, `strength`, `size_strength` | Goal |
| `training_status` | enum | yes | `new`, `returning`, `normal`, `advanced` | Training status |
| `target_days` | int | yes | `2`-`5` | Days available |
| `session_time_band` | enum | yes | `low`, `normal`, `high` | Session time |
| `equipment_pool` | string[] | yes | canonical equipment tags | Equipment |
| `movement_restrictions` | string[] | yes | canonical movement restriction tags | Restrictions |
| `recovery_modifier` | enum | yes | `low`, `normal`, `high` | Recovery |
| `weakpoint_targets` | string[] | yes | max 2 muscles | Weak points |
| `preference_bias` | enum | yes | `free_weights`, `machines_cables`, `mixed` | Preferences |
| `anthropometry_flags` | object | yes | `{long_femurs, long_arms}` booleans | Height/limb answers |
| `bodyweight_regression_flag` | bool | yes | true/false | Bodyweight + movement context |
| `sex_related_physiology_flag` | enum | yes | `off`, `female`, `male`, `intersex`, `self_describe`, `prefer_not` | Optional physiology |
| `starting_rir` | int | yes | `1`-`4` | Derived |
| `high_fatigue_cap` | int | yes | per-session cap, typically `1`-`2` | Derived |
| `weekly_volume_band` | object | yes | `{planned_sets_min, planned_sets_max}` | Derived |
| `major_muscle_floors` | object | yes | chest/back/quads/hamstrings minimum weighted sets | Derived |
| `arm_delt_caps` | object | yes | soft/hard caps + weakpoint allowance window | Derived |
| `core_floor` | int | yes | minimum weekly core weighted sets | Derived |
| `rep_bands` | object | yes | `{main_lift, accessory}` rep ranges | Goal + status |
| `progression_mode` | enum | yes | `reps_first`, `load_first`, `hybrid` | Goal |

## Deterministic Mapping Rules

### Goal mapping
- `Hypertrophy` -> `goal_mode=hypertrophy`, `progression_mode=reps_first`, full archetype volume band.
- `Strength` -> `goal_mode=strength`, `progression_mode=load_first`, lower weekly volume band, heavier main rep bands.
- `Size + Strength` -> `goal_mode=size_strength`, `progression_mode=hybrid`, heavy primary compounds + hypertrophy accessories.

### Training status mapping
- `New` -> `training_status=new`
- `Returning after layoff` -> `training_status=returning`
- `Consistent 6-24 months` -> `training_status=normal`
- `Consistent 2+ years and comfortable near failure` -> `training_status=advanced`

Derived effects:
- New/returning use higher `starting_rir` and stricter `high_fatigue_cap`.
- Advanced permits tighter RIR and higher volume band ceilings.

### Days and time mapping
- `target_days=2` -> deterministic 2-day fallback full body.
- `target_days=3` -> standard generated 3-day full body.
- `target_days>=4` in MVP -> keep generated 3-day baseline (future expansion handles 4-day).

Session time:
- `30-45` -> `session_time_band=low`
- `50-70` -> `session_time_band=normal`
- `75-100` -> `session_time_band=high`

### Equipment and restrictions mapping
- `equipment_pool` becomes hard eligibility filter before scoring.
- `movement_restrictions` become hard movement blocklist/substitution constraints.
- Preferences never override hard restrictions.

### Weak-point mapping
- `weakpoint_targets` capped at max 2.
- Apply weak-point bonus only after `major_muscle_floors` are satisfied.
- Bonus subject to `arm_delt_caps` and fatigue/session-balance guardrails.

### Anthropometry/bodyweight/physiology mapping
- `anthropometry_flags` affect exercise ranking and substitutions only.
- `bodyweight_regression_flag` biases to assisted regression choices where relevant.
- `sex_related_physiology_flag` may influence conservative load seeding tie-breaks only.
- None of these inputs can lower major muscle floors or create separate template families.

### Recovery mapping
- `low` recovery:
  - reduce weekly planned sets band by 10-15%
  - add +1 `starting_rir`
  - lower `high_fatigue_cap` by 1 where feasible
  - defer weak-point extras until floors are met
- `normal` recovery: baseline.
- `high` recovery: allow upper range of status/time band.

## 3-Day Volume Archetype Reference Bands (Generated MVP)
Weighted set floors use deterministic muscle crediting.

| Status | Time band | Planned sets/wk | Chest floor | Back floor | Quads floor | Hamstrings floor | Delt soft cap | Arm soft cap | Core floor | Default RIR | High-fatigue cap/session |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| New/returning | Low | 36-42 | 6 | 8 | 6 | 6 | 8 | 8 | 2 | 3-4 | 1 |
| New/returning | Normal | 42-50 | 8 | 10 | 8 | 8 | 10 | 10 | 4 | 2-3 | 1 |
| New/returning | High | 50-58 | 10 | 12 | 10 | 10 | 12 | 12 | 4 | 2-3 | 1 |
| Normal | Low | 40-48 | 8 | 10 | 8 | 8 | 10 | 10 | 3 | 3 | 1 |
| Normal | Normal | 50-60 | 10 | 12 | 10 | 10 | 12 | 12 | 4 | 2-3 | 1-2 |
| Normal | High | 60-72 | 12 | 14 | 12 | 12 | 14 | 14 | 4 | 2 | 2 |
| Advanced | Low | 44-54 | 8 | 10 | 8 | 8 | 10 | 10 | 4 | 3 | 1 |
| Advanced | Normal | 58-70 | 12 | 14 | 12 | 12 | 14 | 14 | 4 | 2 | 2 |
| Advanced | High | 70-84 | 14 | 16 | 14 | 14 | 16 | 16 | 6 | 1-2 | 2 |

## Starting Load Policy
Priority order:
1. Prior reliable logs for same exercise/family.
2. Recent self-reported bests (if provided).
3. Conservative seed + first-session RIR calibration.

Demographics-only load prediction is disallowed as a primary method.

## Determinism Requirements
- Same onboarding payload must yield the same `GenerationProfile`.
- Missing optional fields must map to explicit defaults.
- Mapping and guardrails must be testable without user-interface dependencies.
