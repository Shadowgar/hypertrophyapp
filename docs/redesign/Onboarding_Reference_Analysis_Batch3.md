# Onboarding Reference Analysis - Batch 3

Last updated: 2026-03-06

Scope: final screenshot batch provided by user.
Goal: capture late-stage personalization, permissions, and workout generation handoff behavior.

## New Steps Observed

1. Notification permission prompt
- Message: reminders/rest timer/chat notifications keep user on track.
- Actions:
  - Primary: `Enable`
  - Secondary: `I'll do this later`
- Implication: explicit optional opt-in prompt before/during final onboarding.

2. Primary workout location
- Question: `Where will you be primarily working out?`
- Options:
  - Gym
  - Home
- Screen includes `Skip` action.

3. Gym setup detail (branch after `Gym`)
- Question: `Which best describes your gym setup?`
- Options are capability tiers, e.g.:
  - Squat rack + dumbbells + machines + cable weights
  - Smith machine + dumbbells + machines + cable weights
  - Dumbbells + machines + cable weights
  - Machines + cable weights
- Screen includes `Skip`.

4. Strength training experience
- Question: `How much experience do you have with strength training?`
- Options with descriptive copy:
  - Beginner
  - Intermediate
  - Advanced
- Screen includes `Skip`.

5. Preferred workout duration
- Question: `How long would you like your workouts to be?`
- Options:
  - 30 minutes
  - 45 minutes
  - 60 minutes
- Screen includes `Skip`.

6. Days per week availability
- Question: `How many days a week can you work out?`
- Observed options:
  - 3 days
  - 4 days
- Screen includes `Skip`.

7. Plan generation loading state
- Transitional screen: `Creating your workouts...`
- Implication: onboarding answers are immediately consumed to create personalized first plan.

## Flow Inference Updates

- Late-step onboarding appears to support skip behavior for optional personalization refinements.
- Branching logic is visible:
  - Location selection drives equipment follow-up question set.
- Onboarding transitions directly into deterministic initial plan generation.

## Additional Data Model Implications For HyperTrophy

Recommended new fields:
- `notifications_opt_in` (boolean)
- `workout_location_primary` (enum: `gym`, `home`, `other`)
- `gym_setup_tier` (enum)
- `strength_experience_level` (enum: `beginner`, `intermediate`, `advanced`)
- `preferred_workout_duration_minutes` (enum/int)
- `days_available` (already exists; map from onboarding step)
- `onboarding_plan_generated_at` (datetime)

## Additional Instrumentation Events

- `onboarding_notifications_prompt_viewed`
- `onboarding_notifications_enabled`
- `onboarding_notifications_deferred`
- `onboarding_step_skipped`
- `onboarding_branch_entered` (e.g., `location:gym`)
- `onboarding_plan_generation_started`
- `onboarding_plan_generation_completed`
- `onboarding_plan_generation_failed`

## Product Considerations For HyperTrophy

- Preserve skip options for non-blocking questions while requiring minimum viable plan inputs.
- Treat equipment capability tier as a first-class planning constraint.
- Show explicit loading and fallback behavior if initial plan generation fails.

## Remaining Open Questions

- Home equipment branch screens were not shown in this batch.
- Notification permission denial recovery copy/state not shown.
- Error UX for failed plan generation was not shown.
