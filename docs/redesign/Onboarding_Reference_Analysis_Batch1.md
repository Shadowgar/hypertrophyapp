# Onboarding Reference Analysis - Batch 1

Last updated: 2026-03-06

Scope: first 10 screenshots provided by user.
Goal: extract onboarding flow logic, captured fields, and tracking implications.

## Observed Funnel Structure

1. Intro carousel (multiple slides)
- Slide pattern: short value-prop headline + one visual cluster + concise supporting copy.
- Persistent CTAs:
  - primary: `Get Started`
  - secondary: `I already have an account`
- Dot pagination indicates slide position.

2. Guided multi-step questionnaire
- One question per screen.
- Back arrow for step navigation.
- Segmented progress bar showing total onboarding length and current progress.
- Large tap targets for options.
- `Next` is disabled until input is valid.

## Questions/Inputs Observed

From screenshots, the app asks and tracks:

1. Context labels (shown in intro):
- Travel
- Freestyle
- Gym
- Home
- Prenatal

2. Gender
- Male
- Female
- Prefer not to say

3. Primary fitness goal
- Build muscle
- Lose fat
- Gain strength
- Improve overall health
- Improve performance
- Something else

4. Height
- Unit toggle: `in` / `cm`
- Numeric input (or split ft/in input when imperial)

5. Weight
- Unit toggle: `lbs` / `kg`
- Numeric input

6. Birthday
- Date input (`mm/dd/yyyy`)
- Derived metric: age

7. Strength training age
- I am just getting started
- Less than 1 year
- 1-2 years
- 2-5 years
- More than 5 years

## Data Model Implications For HyperTrophy

Recommended onboarding profile fields:
- `sex_or_gender` (string enum, with `prefer_not_to_say`)
- `primary_goal` (enum + optional free text)
- `training_environment_preferences` (multi-select: gym/home/travel/etc.)
- `height_value` + `height_unit`
- `weight_value` + `weight_unit`
- `birthday` (date, derive age server-side)
- `training_age_bucket` (enum)

## Instrumentation Events To Capture

Recommended onboarding analytics events:
- `onboarding_intro_slide_viewed`
- `onboarding_intro_get_started_clicked`
- `onboarding_login_clicked`
- `onboarding_step_viewed`
- `onboarding_step_completed`
- `onboarding_step_back_clicked`
- `onboarding_validation_error`
- `onboarding_completed`

Include payload keys:
- `step_id`
- `step_index`
- `total_steps`
- `time_on_step_ms`
- `field_validation_state`

## Product Constraints Inferred

- Keep one cognitive task per screen.
- Keep primary CTA fixed near bottom.
- Keep visual progress explicit and stable.
- Keep all key profile inputs explicit (do not infer hidden defaults).

## Open Questions For Next Screenshot Batch

- Additional profile questions after training-age step.
- Program preference and schedule selection screens.
- Equipment granularity and injury constraints collection.
- Account creation timing relative to questionnaire completion.
- Skip logic behavior by goal or training experience.

## Follow-Up

- See `docs/redesign/Onboarding_Reference_Analysis_Batch2.md` for additional observed onboarding steps and account-transition behavior.
