# Manual qualification protocol

Planned, revision/environment-scoped protocol under [test strategy](test-strategy.md), [release gates](release-gates.md), [UX requirements](../requirements/catalog.md#ux). No new browser/device session was performed here. [Legacy tester runbook](../testing/INTERNAL_TESTER_RUNBOOK.md) retains original target-device ideas; actual supported device/browser policy is pending.

Use an explicitly approved isolated/staging environment and synthetic account/history, never production data or inherited database defaults. Record revision, device/browser/version, environment, fixture, exact expected/observed steps, time, result and sanitized artifact. Capture issues with the [template](../problems/issue-template.md), without passwords, reset credentials, personal data or sensitive URLs.

Cover register/sign-in/recovery, mode consent/onboarding, preview/activation, manual actual dates, Today resume, set logging/retry/undo, source-approved substitution confirmation, load/effort override, review/history and account switching. Verify displayed rationale against actual decision facts and missing-evidence states. For affected mobile flows include keyboard/focus/screen reader, tap/overlay behavior, background timer/resume and network loss. Offline writes stay deferred until their contract is accepted.

Report data loss/identity leakage, blocked auth/runner or unsafe/unexplained prescription immediately to the approved review channel; do not automatically send external messages. A synthetic functional loop is not longitudinal felt-behavior, real-device reliability or scientific outcome evidence. Preserve unfinished legacy qualitative gates in the [task register](../audits/2026-09-28-legacy-task-register.md).
