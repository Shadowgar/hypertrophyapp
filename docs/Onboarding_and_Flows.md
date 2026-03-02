# Onboarding and Core Flows

## Onboarding Flow
1. User opens `/onboarding`.
2. User registers account (email/password/name).
3. User submits profile: age, weight, gender, split preference, days/week, nutrition phase, calories/macros.
4. App stores JWT locally and persists profile via `/profile`.

## Weekly Check-In Flow
1. User submits check-in via `/weekly-checkin` with current bodyweight + adherence score.
2. API stores check-in and uses profile phase context for next planning decisions.

## Generate Week Flow
1. User triggers `/plan/generate-week`.
2. API loads canonical template from `programs/`.
3. Core engine generates deterministic sessions with recommended working weights.
4. Plan saved and returned to client.

## Start Workout Flow
1. User opens `/today`.
2. App requests `/workout/today`.
3. API returns today or next eligible session with warmups and work sets.

## Log Sets Flow
1. User logs each set via `/workout/{id}/log-set`.
2. API writes logs and updates progression state.
3. Future weight recommendations derive from updated deterministic state.

## History Flow
1. User opens `/history`.
2. App requests `/history/exercise/{id}`.
3. API returns set logs for trend review and confidence checks.
