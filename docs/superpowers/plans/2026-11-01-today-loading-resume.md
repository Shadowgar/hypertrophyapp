# Today loading and reliable resume implementation plan

> **For agentic workers:** Use superpowers:executing-plans and test-driven-development to implement task-by-task.

**Goal:** Reduce avoidable Today reads/waiting and preserve account-scoped workout drafts across transient verification failures.

**Architecture:** Keep server-owned training mode, local date, occurrence, source and command authorities. Remove the diagnostic health ping as a prerequisite for an actual authenticated workout read; resolve optional progress and soreness independently. Retain an unverified current view in memory, hidden and unable to write until revalidated. Bound only selected GET requests; never time out/retry a mutation automatically.

**Tech Stack:** Existing React/Next, typed API client, Vitest, real isolated API/PostgreSQL, production-built browser measurements.

**Spec:** Owner's 2026-11-01 next package under #103/#105; existing PERS-002, Today performance evidence/closeout, execution/date/history contracts and merged PR #137.

## Global constraints

- Base06e910896203355c11815d3e586e1dec6d8e0c3e mainCI41361759667 andCodeQL41361759384 passed, including private source fidelity. Release skipped. No correction needed.
- No production data/config/control changes, migration, merge/deploy, reset or training-policy/source-artifact change.
- Preserve starting-weight UI, stable Save Set, exact pending commands, consent, recovery and actual-date history. No offline logging or cached prescription authority.
- Reuse existing investigation. Fresh matched synthetic measurements only; no repeat of the prior 96-navigation cold-start study. No production/iPhone percentile claim.

## Review focus

- Late/aborted reads must not paint another account or reopen an unverified runner.
- Deadline handling must affect GETs only, with no automatic mutation retry or fabricated success.
- Soreness Skip must still recheck local date and handle rollover; saving a report must still refresh source constraints.
- Same-occurrence refresh failures retain drafts; different occurrence, auth and mandatory conflicts must retire old authority.
- Background progress cannot overwrite a newer receipt/correction/undo or postpone the optional prompt.

### Task 1: Bounded reads and precise loading/recovery

**Files:** apps/web/lib/api.ts; components/flexible-training.tsx; app/today/page.tsx; focused API-client/Today/Flexible tests.
**Interfaces:** Existing server endpoints/payloads unchanged. 15s deadline for selected GETs only. Optional training-read state callback; existing server decision callback stays authoritative.

- [x] Write failing tests for stalled reads, no health prerequisite, training lookup errors, phase-correct date errors and late/account-switch responses. Prove writes have no new timeout.
- [x] Observe red; implement bounded GET helper and readable checking/error/retry states without treating missing mode as calendar or bypassing server gates.
- [x] Write failing tests for prompt independent of progress and no second Today/progress after Skip; preserve date rollover and saved-report reload tests.
- [x] Observe red; launch progress asynchronously and reuse the verified occurrence on same-day Skip only.
- [x] Write failing refresh/recovery tests: hidden stale controls, same-occurrence draft preserved, mutation guards while unverified, mandatory conflict/account retirement, pending undo recovery.
- [x] Observe red; retain transiently unverified state without making it writable; keep the existing canonical draft/receipt owners.
- [x] Run focused loading, soreness, Flexible, state/unit/retry/correction and starting-weight regressions; typecheck/lint. Commit.

### Task 2: Matched measurements, review and PR qualification

**Files:** docs/evidence/today-loading-resume-2026-11-01; narrowly necessary tests.
**Interfaces:** Same production build/rewrite and verified synthetic database/fixtures for baseline/candidate. External instrumenter reused from prior package; no runtime policy instrumentation.

- [x] Verify protected main/current checks and disposable target before imports/bootstrap; capture baseline 18 visits (3 per mode/condition), request counts and API phases.
- [x] Build candidate sequentially; measure identical native and controlled-delay cases, retain all samples/ranges and report limits.
- [x] Real browser/API recovery, reload/pending set and unit/account isolation journeys; source/history comparison. No writes to the four timing-mode accounts.
- [x] Fresh changed-file review and scoped security review; fix actual findings with focused red/green tests.
- [ ] Create one focused PR, keep103/105open and run normal final-head CI/CodeQL/GitGuardian. Record SHA/results/checkpoint; do not merge/deploy.
