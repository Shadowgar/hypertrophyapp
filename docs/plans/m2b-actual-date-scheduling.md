# M2B-1 actual-date scheduling implementation plan

Status: owner-authorized implementation in the 2026-10-06 attached task. Deployment of M1-C is separately authorized; M2B migrations, deployment and merge are forbidden in this task. ADR-007 remains Proposed.

Implementation and independent review fixes are on [PR #76](https://github.com/Shadowgar/hypertrophyapp/pull/76); [qualification evidence and limits](../evidence/2026-10-06-m2b-actual-date-scheduling.md). Local focused/migration/browser qualification is complete within that record; final exact-head hosted CI/Codex review is tracked on the PR. No owner acceptance is inferred.

Goal: select actual current-week local dates, preview and activate lossless authored placement, and route Today/Week by those dates.

Specification: the attached owner task, docs/contracts/selected-date-scheduling.md and docs/contracts/execution-plan.md. Preserve M1-C relationship/order/dose and M1-B source-scoped substitution boundaries. No external calendars, runtime LLM, load intelligence or generated redesign.

## Decisions and interfaces

Use a nullable users.scheduling_timezone for the explicitly confirmed IANA timezone. Week is Monday–Sunday, date-only, with explicit aware planning instant. Allow 2–5 dates, including elapsed current-week dates as explicit placements only; never invent performed history. UI warns when selecting elapsed dates. No UTC workout instant is manufactured.

POST /plan/selected-dates/preview and POST /plan/generate-week consume GenerateWeekPlanRequest {template_id, week_start, selected_dates, timezone, expected_placement_revision}; return the existing week-plan shape with schedule metadata. Preview performs no writes, including profile/binding changes. GET /plan/scheduling-context?timezone=… returns {timezone, local_today, week_start, selected_dates, placement_revision, plan}. A persisted scheduling timezone takes precedence; new users explicitly confirm the browser-suggested timezone at activation.

Scheduling owns placement only. Enumerate M1-C contiguous source-unit allocations, respect hard relationships and limits, score actual consecutive-date overlapping work as an explicit advisory policy, and use workload balance and stable cuts as tie-breakers. Never claim clinical/recovery qualification. Disclose unknown adjacent-week context, exact calendar gaps, source/rule identity and estimated duration limitations.

Persist nullable placement metadata additively; no legacy date backfill. Same-count unstarted revisions retain plan/workout/exercise identities and frozen prescriptions. A changed date count explicitly supersedes an entirely unstarted plan with retained placement history and new occurrence identities; no automatic move once an execution or consent snapshot exists. Lock the user row for revision/logging serialization. Legacy count/frequency commands cannot replace selected-date plans. Current-week routing ignores future/old plans and uses the persisted timezone. Completed Today remains on the correct occurrence, never advances to another selected date.

## Tasks and acceptance

- [x] 1. Verify current-main deployed API/web source, health/pages and desktop/mobile smoke. Preserve the existing log. Do not migrate or manufacture history.
- [x] 2. Core: add meaningful failing date/gap/relationship/dose/repeated-slot tests; implement date-sensitive ordered allocation, validation, spacing trace and explicit infeasibility. Keep existing M1-C API unchanged unless optional inputs supplied.
- [x] 3. API: add failing preview/no-write, revision, ownership, timezone, local Today/rest/resume/completed, cross-week and legacy-bypass tests. Implement context/preview/activation, additive 0021 migration and frozen execution date ownership.
- [x] 4. Web: add failing current-week selection/preview/exact-date/stale-week/rest tests. Implement accessible simple picker, visible explicit timezone, warnings, preview then activation, exact Week dates and Today rest state.
- [x] 5. Rehearse 0020→0021 on isolated PostgreSQL with synthetic legacy rows, preserving unknown dates and history; qualify locking races. Run focused suites during development; final relevant broader suites once and compare baseline failures.
- [ ] 6. Playwright desktop/mobile against controlled synthetic API/database; collect rendered interaction, ordering, console and layout evidence. Review sensitive API/schema boundaries with Codex Security. Commit, push and PR, monitor CI/Codex threads and mergeability; stop unmerged/unreleased for review.

Review focus: timezone/week rollover while picker is open; multiple program plans for one date; legacy frequency regeneration bypass; preview autoflush; count changes reusing slot identities; logging/substitution racing with reschedule; undone sets still freezing execution snapshots.

Task 6 is partly complete: actual desktop/mobile qualification and independent source reviews are recorded, PR #76 is pushed and initial CI/review findings are handled. Exact-head post-fix CI/Codex monitoring is ongoing at this documentation revision. Managed security artifact retention remains blocked by global storage permissions; no sealed scan is claimed. This is an explicit qualification gap, not permission to change global storage or release the candidate.
