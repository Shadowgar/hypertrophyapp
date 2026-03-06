# Onboarding Reference Analysis - Batch 2

Last updated: 2026-03-06

Scope: second screenshot batch provided by user.
Goal: extend field/flow mapping from Batch 1 with additional onboarding steps and account transition behavior.

## New Steps Observed

1. Current strength training frequency
- Question: `How often do you currently strength train?`
- Options:
  - Never
  - Once in a while
  - 1-2 times / week
  - 3-4 times / week
  - 5+ times / week

2. Motivation driver
- Question: `What helps you stay motivated to work out?`
- Options include title + explanatory subtitle:
  - Accountability (Having others keep me accountable)
  - Competition (Turning it into a challenge or friendly competition)
  - Fun (Making it fun and part of my lifestyle)
  - Self-Motivated (I stay motivated on my own but enjoy helping others)

3. Biggest obstacle
- Question: `What do you feel is the biggest obstacle getting in the way of your progress?`
- Options:
  - Lack of motivation
  - Not sure what to do to get results
  - Not enough time to work out
  - Dealing with an injury
  - Something else
  - None right now
- Selection behavior observed:
  - Single-select
  - Selected row gets highlighted and check icon
  - `Next` button becomes enabled after selection

4. Name capture sequence
- Question screen uses same heading: `What should we call you?`
- Two consecutive inputs:
  - First name (required)
  - Last name (optional)

5. Questionnaire completion interstitial
- Confirmation card: `Got it, thanks!`
- Copy indicates answers will personalize app experience.
- Two actions:
  - Primary: `Continue`
  - Secondary: `Go Back`

6. Account creation after questionnaire
- Header: `Create account`
- Inputs:
  - Email
  - Password
- Primary CTA: `Continue`
- Flow implication: profile questionnaire occurs before auth creation.

7. Post-account sync permission step
- Screen: `Set up syncing`
- Context: import cardio/nutrition data and sync strength data to health platform.
- Actions:
  - Primary: enable platform health integration (`Enable Apple Health`)
  - Secondary: defer (`I'll do this later`)

## Flow Inference Updates

- Questionnaire-first architecture reduces account creation friction and delays commitment until personalization value is demonstrated.
- Progress indicator appears consistent and long-form (roughly 12 total steps shown by segmented bar).
- Validation pattern is strict and explicit:
  - CTA disabled until current step has valid input.
  - Back navigation always visible.

## Additional Data Model Implications For HyperTrophy

Recommended new onboarding fields:
- `current_strength_frequency_bucket` (enum)
- `motivation_driver` (enum)
- `primary_obstacle` (enum + optional custom text for `something_else`)
- `first_name` (required)
- `last_name` (optional)
- `health_sync_opt_in` (boolean)
- `sync_provider_status` (enum: `pending`, `enabled`, `deferred`)

## Additional Instrumentation Events

- `onboarding_step_option_selected`
- `onboarding_summary_interstitial_viewed`
- `onboarding_summary_continue_clicked`
- `onboarding_summary_go_back_clicked`
- `onboarding_account_create_viewed`
- `onboarding_sync_prompt_viewed`
- `onboarding_sync_enabled`
- `onboarding_sync_deferred`

## Product Considerations For HyperTrophy

- Preserve deterministic coaching inputs while avoiding unnecessary collection burden.
- Keep social/community motivation fields optional if not yet used by runtime logic.
- Gate optional integrations (health sync) after account creation with an explicit skip path.

## Follow-Up

- See `docs/redesign/Onboarding_Reference_Analysis_Batch3.md` for late-stage onboarding steps (notifications, location/equipment branch, duration, weekly availability, and plan-generation handoff).

## Remaining Open Questions

- Injury-specific follow-up branch behavior when `Dealing with an injury` is selected.
- Home-equipment branch options and mapping granularity.
- Error UX for account creation, sync permission denial, and initial plan generation failure.
