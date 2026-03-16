# Onboarding and Core Flows

## Onboarding Flow
1. User opens `/onboarding`.
2. App walks the user through intro slides and one-question-per-step onboarding inputs (with optional skips on non-critical questions).
3. Questionnaire progress auto-saves in browser-local draft storage and restores on revisit.
4. User reaches account step and registers/logs in (email/password/name).
5. App stores JWT locally and persists profile + `onboarding_answers` via `/profile`.
6. App attempts initial workout generation via `/plan/generate-week` and redirects to `/today` on success path.

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
2. App requests `/history/analytics` and `/history/calendar`.
3. Calendar renders daily completion indicators, streak summaries, PR badges, and optional completion/program/muscle filtering.
4. User clicks a day cell.
5. App requests `/history/day/{day}`.
6. API returns workout/exercise/set detail, planned-vs-performed deltas, and planned-only missed-day detail when applicable.
7. UI supports previous same-weekday jump and same-weekday delta comparison cards (sets/volume/PR-day count).
8. App optionally uses `/history/exercise/{id}` for exercise-specific trend deep dives.






## Progress Sync (2026-03-16)
- Repository state at commit `c4aab67` on `main`.
- Validation baseline:
  - Core engine: `324 passed`
  - API: `197 passed`
  - Web tests: `18 test files passed`, `41 tests passed`
- Drift prevention protocol: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

