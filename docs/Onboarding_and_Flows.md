# Onboarding and Core Flows

## Onboarding Flow
1. User opens `/onboarding`.
2. User registers account (email/password/name).
3. User submits profile: age, weight, gender, split preference, training location, equipment profile, days/week, nutrition phase, calories/macros.
4. App stores JWT locally and persists profile via `/profile`.

## Weekly Check-In Flow
1. User submits check-in via `/weekly-checkin` with current bodyweight + adherence score.
2. API stores check-in and uses profile phase context for next planning decisions.

## Generate Week Flow
1. User triggers `/plan/generate-week`.
2. API loads canonical template from `programs/`.
3. Core engine filters exercises/substitutions by equipment profile, auto-selects the first compatible substitute when needed, and generates deterministic sessions with recommended working weights.
4. Plan saved and returned to client.

## Start Workout Flow
1. User opens `/today`.
2. App requests `/workout/today`.
3. API returns today or next eligible session with warmups and work sets.

## Substitution Flow
1. User taps `I don’t have this equipment` on an exercise card.
2. App opens a substitution picker tied to that exercise slot.
3. User selection is persisted for the current session so slot intent + notes remain intact.

## Log Sets Flow
1. User logs each set via `/workout/{id}/log-set`.
2. API writes logs with both `primary_exercise_id` (slot intent) and `exercise_id` (performed variant), then updates progression state.
3. Future weight recommendations derive from updated deterministic state.

## History Flow
1. User opens `/history`.
2. App requests `/history/exercise/{id}`.
3. API returns set logs for trend review and confidence checks.
