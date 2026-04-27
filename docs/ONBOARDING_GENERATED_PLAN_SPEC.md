# Onboarding Spec: Generated Plan (Deterministic)

Last updated: 2026-04-27
Status: active specification for generated `Make me a plan` onboarding
Scope: generated path only (`full_body_v1` and successors)

## Purpose
This spec defines the minimum onboarding inputs required to produce a deterministic generated hypertrophy plan without runtime LLM usage.

Design principle: collect only fields that materially change training dose, distribution, selection, or calibration.

## Product Boundaries
- This spec governs generated planning only.
- Authored templates (`phase_1`, `phase_2`) remain separate products and are not redefined here.
- Onboarding answers must map into a deterministic `GenerationProfile` before generation.

## Onboarding Flow
1. Safety gate
2. Core required inputs (goal, days, session time, training status, equipment, movement restrictions)
3. Optional improve-fit inputs (weak points, preferences, anthropometry, bodyweight, physiology, recovery)
4. Deterministic profile derivation
5. Week generation + Week 1 load calibration via RIR

## Required Fields (MVP)

| Field | Exact question text | Answer options | Validation | Default/fallback |
|---|---|---|---|---|
| Safety gate | Before we build your plan: do any of these apply right now? Chest pain with exercise; fainting/dizziness during exercise; a clinician told me not to lift; recent surgery/injury needing restrictions. | Multi-select chips + `None` | Required | If any selected: apply conservative safety pathway + referral copy |
| Goal | What should this plan prioritize for the next 8-12 weeks? | `Hypertrophy`, `Strength`, `Size + Strength` | Required single select | `Hypertrophy` |
| Days available | How many days per week can you realistically lift? | Integer stepper: `2`-`5` | Required | `3` |
| Session time | What session length can you reliably finish most weeks? | `30-45 min`, `50-70 min`, `75-100 min` | Required single select | `50-70 min` |
| Training status | Which best describes your recent lifting history? | `New`, `Returning after layoff`, `Consistent 6-24 months`, `Consistent 2+ years and comfortable near failure` | Required single select | `Returning after layoff` |
| Equipment | Which equipment do you reliably have access to? | Multi-select equipment tags | Required, min 1 | Quick-start fallback: `Bodyweight + dumbbells` |
| Movement restrictions | Anything we should avoid or modify right now? | Multi-select: `Deep knee flexion`, `Overhead pressing`, `Barbell from the floor`, `Long-length hamstrings`, `Unsupported bent-over rowing`, `None`, `Other` | Optional but strongly prompted | `None` |

## Optional "Improve Fit" Fields

| Field | Exact question text | Answer options | Validation | Default/fallback |
|---|---|---|---|---|
| Weak points | Which muscle groups do you most want to bring up? Pick up to 2. | Multi-select (max 2) | Optional | `None` |
| Preferences | When multiple options work, what do you usually prefer? | `Free weights`, `Machines & cables`, `Mixed` | Optional single select | `Mixed` |
| Height | How tall are you? | Numeric with unit toggle | `120-230 cm` or `4'0"-7'6"` | `Unknown` |
| Bodyweight | What is your current body weight? | Numeric with unit toggle | `35-250 kg` or `80-550 lb` | `Unknown` |
| Sex-related physiology | Optional: would you like us to use sex-related physiology to refine exercise defaults and load seeding? If yes: Female / Male / Intersex / Self-describe / Prefer not to say | Optional toggle + single select | Optional | Toggle off + `Prefer not to say` |
| Limb proportions | Optional: if this sounds like you, choose your build. Long thighs vs torso / Long arms vs height / Both / Neither / Not sure | Single select | Optional | `Not sure` |
| Recovery | How would you rate your recovery capacity right now? | `Low`, `Normal`, `High` | Optional single select | `Normal` |

## Validation Rules
- Hard-fail only on required fields and invalid enum/range values.
- Movement restrictions are movement-based, not diagnosis-based.
- Weak points are capped to max 2 selections.
- If optional fields are missing, generator must still produce a viable conservative plan.
- No gender-stereotype branching is allowed.

## Defaults and Fallbacks
- Default plan skeleton: deterministic 3-day full body.
- 2-day users: deterministic 2-day fallback template.
- 4+ day users in MVP: remain on 3-day default unless future split expansion is enabled.
- Skipped improve-fit fields: use neutral defaults and conservative load seeding.

## Privacy Notes
- Treat movement restrictions, physiology selection, and body metrics as sensitive health-adjacent data.
- Collect only fields used by deterministic profile derivation.
- Prefer structured options over free-text diagnosis fields.
- Do not share onboarding health-adjacent fields with ad-network style consumers.

## How Answers Affect Generation (Deterministic)
- Goal: rep-band emphasis, progression mode, volume modifier.
- Days + time: session density, slot count, weekly planned sets band.
- Training status + recovery: starting RIR, high-fatigue caps, progression conservatism.
- Equipment + restrictions: eligible exercise pool + substitution constraints.
- Weak points: bounded bonus window only after major floors are satisfied.
- Anthropometry + bodyweight + physiology flags: exercise fit, substitution ranking, bodyweight regressions, conservative load seeding tie-breaks.

## Non-Goals
- No runtime LLM personalization.
- No diagnosis logic.
- No separate men/women hypertrophy templates.
- No demographic-only starting load prediction.
