# Onboarding Reference Process Map (Batches 1-3)

Last updated: 2026-03-06

Purpose: single consolidated flow map extracted from all shared onboarding screenshots.

## End-to-End Sequence (Observed)

1. Intro carousel
- Multiple value-prop slides.
- Primary CTA: `Get Started`.
- Secondary CTA: `I already have an account`.

2. Questionnaire (one question per step)
- Gender
- Primary fitness goal
- Height (unit-aware)
- Weight (unit-aware)
- Birthday
- Strength training age bucket
- Current weekly strength frequency
- Motivation driver
- Biggest obstacle
- First name (required)
- Last name (optional)

3. Questionnaire completion interstitial
- `Got it, thanks!`
- Actions: `Continue` / `Go Back`.

4. Account creation
- Email + Password.

5. Optional integrations and permissions
- Health sync prompt (`Enable Apple Health` / defer).
- Notification prompt (`Enable` / `I'll do this later`).

6. Late personalization (skip-capable)
- Primary workout location (Gym/Home).
- Gym setup tier (if Gym branch).
- Strength experience level.
- Preferred workout duration.
- Days per week availability.

7. Plan-generation handoff
- Loading state: `Creating your workouts...`.

## Inputs That Feed Deterministic Plan Generation

Required (core):
- `days_available`
- `workout_location_primary`
- equipment capability (gym/home tier)
- `strength_experience_level` or equivalent training-age proxy
- `preferred_workout_duration_minutes`
- goal/obstacle context where used by template/rule selection

Optional (non-blocking but useful):
- motivation style
- notification preference
- sync preference
- social/community preference

## Behavioral Patterns To Preserve

- Single cognitive task per screen.
- Explicit progress bar with back navigation.
- Disabled `Next` until valid answer.
- Explicit skip for non-critical late questions.
- Immediate post-onboarding plan generation with visible loading state.

## Remaining Unknown Branches

- Home-equipment detail branch.
- Injury follow-up branch.
- Error-state screens for account creation/sync/plan-generation failure.
