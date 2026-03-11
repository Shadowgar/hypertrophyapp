# Internal Tester Runbook

Last updated: 2026-03-11

## Goal

Run the core hypertrophy coaching loop on desktop and mobile browsers and capture issues clearly enough that engineering can reproduce and fix them.

## Target Platforms

- Desktop:
  - Chrome
  - Safari
  - Edge
- Mobile browser:
  - iPhone Safari
  - Android Chrome

## Core Flows To Test

1. Register or sign in
2. Complete onboarding
3. Generate a week
4. Open `Today`
5. Log at least one set in a workout
6. Submit a weekly review
7. Open history and inspect a past day

## What To Capture For Every Issue

- device type
- browser
- exact page/flow
- exact steps
- expected result
- actual result
- screenshot or screen recording if possible

## Coaching-Specific Issues

If the issue is about the coaching itself, also capture:

- recommendation ID, if shown
- visible rationale text
- whether the issue happened on:
  - onboarding
  - generate-week
  - today
  - log-set
  - weekly review
  - history

## Specific Things To Watch For

- layout breaks on small screens
- buttons that are hard to tap during workouts
- clipped cards or horizontal scrolling
- wrong or missing transition guidance after a completed block
- missing substitution guidance
- confusing progression or phase explanations
- flows that require manual refresh or force sign-in again unexpectedly

## Minimum Test Session

Each internal tester should complete:

1. one onboarding flow
2. one generated week
3. one workout logging flow
4. one weekly review flow

## Escalation

Escalate immediately if:

- login/register is blocked
- generate-week fails
- workout logging loses data
- weekly review cannot be submitted
- a coaching recommendation is clearly wrong and not explainable from the visible rationale
