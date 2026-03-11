# User Testing Rollout Plan

> **For Codex:** Keep this aligned with `docs/Master_Plan.md`, `docs/GPT5_MINI_HANDOFF.md`, and `docs/GPT5_MINI_SUCCESS_PLAN.md` as release readiness evolves.

**Goal:** Create a practical path for real user testing on desktop and mobile without derailing the deterministic coaching rebuild.

**Principle:** User testing should begin on the responsive web product first. We do not need a native app to start learning from real users. The first beta path should validate onboarding, program generation, workout execution, weekly review, and history across desktop browsers and mobile browsers.

## Rollout Stages

### Stage 0: Internal Readiness Gate
Before any outside testing, all of the following must be true:
- adaptive-gold runtime path is stable across its authored mesocycle
- onboarding works end to end on desktop and mobile-sized viewports
- `/today`, `/workout/{id}/log-set`, `/weekly-review`, and `/history` all work without manual DB intervention
- auth recovery path is usable for test accounts
- critical deterministic coaching traces are present for support/debugging

### Stage 1: Internal Dogfooding
Audience:
- project owner
- 1-3 trusted internal testers

Platforms:
- desktop browser: Chrome, Safari, Edge
- mobile browser: iPhone Safari, Android Chrome

Scope:
- create account
- complete onboarding
- generate week
- run at least 3 workouts
- submit one weekly review
- inspect history/calendar

Instrumentation:
- manual bug log tied to exact flow and device
- capture screenshots for UI regressions
- record decision traces for coaching complaints

Success criteria:
- no blocker in auth/onboarding/workout logging
- no deterministic coaching mismatch that cannot be explained from saved trace/state
- no mobile layout break that prevents core flows

### Stage 2: Closed Beta
Audience:
- 10-25 real hypertrophy trainees
- mixed desktop/mobile usage
- at least a few users on limited-equipment and constrained-schedule profiles

Platforms:
- hosted web app
- mobile browsers first, optional add-to-home-screen second

Scope:
- 2-4 week test window
- require at least one onboarding completion, one generated week, and one completed workout from each tester
- encourage weekly review submission and subjective feedback on plan quality

Feedback collection:
- structured form after onboarding
- structured form after first workout
- weekly form for usability + coaching quality
- free-text notes for pain/equipment/time issues

Success criteria:
- users can independently complete the main loop without developer help
- mobile browser experience is good enough for in-workout logging
- reported coaching decisions are explainable and mostly sensible
- top issues are concentrated in known gaps, not random instability

### Stage 3: Expanded Beta / Soft Launch Readiness
Audience:
- broader external beta

Required before expansion:
- more than one validated gold/runtime program path
- stronger canonical exercise-library coverage
- broader mini/full validation confidence
- bug triage process in place
- support/debugging playbook for user-facing coaching complaints

## Desktop and Mobile Testing Matrix

### Core flows to test everywhere
- register/login
- onboarding draft save/restore
- profile save
- generate week
- workout today
- log set
- substitution guidance visibility
- weekly review submit
- history calendar/day detail

### Desktop-specific checks
- dense plan/history layouts remain readable
- hover and click states are clear
- long-form explanations and traces are inspectable

### Mobile-specific checks
- large tap targets during workout logging
- no clipped cards or horizontal overflow
- keyboard interaction does not break logging forms
- workout flow remains usable one-handed
- slow network / resume behavior is tolerable

## Minimal Product Work Needed Before Real User Testing
1. Stable hosted environment for testers
2. Seeded/staging-safe auth and reset workflow
3. Clear bug-report channel
4. Responsive QA pass for onboarding, today, weekly review, and history
5. Basic release notes / known-issues page for testers

## What Not To Do Yet
- do not wait for native mobile apps before testing
- do not broaden to many programs before the first deterministic runtime path is trusted
- do not use user testing to paper over missing deterministic traces
- do not promise AI-style coaching beyond what the deterministic engine can explain today

## Immediate Next Actions
1. Finish the adaptive-gold 10-week authored mesocycle and keep it stable
2. Run a focused responsive QA pass on desktop and mobile browser viewports
3. Add a lightweight tester runbook and issue template
4. Start internal dogfooding on web for both PC and mobile browsers

Supporting docs:
- `docs/testing/INTERNAL_TESTER_RUNBOOK.md`
- `docs/testing/INTERNAL_TEST_ISSUE_TEMPLATE.md`
