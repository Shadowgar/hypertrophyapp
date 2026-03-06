# Hyperdrive Screenshot Parity Checklist

Purpose: capture before/after parity checkpoints for key app routes affected by the Phase 14 visual pass.

## Capture Rules
- Use the same viewport for both captures: `390x844` (mobile baseline).
- Capture each screen in the same state and data context where possible.
- Include the command dock in all route-level screenshots.
- Store files under:
  - `docs/ui-parity/before/`
  - `docs/ui-parity/after/`
- Naming format: `<route>-<state>.png`.

## Key Screens (Before/After)

| Route | State | Before Image | After Image | Parity Notes |
| --- | --- | --- | --- | --- |
| `/` | Landing with CTA stack visible | `docs/ui-parity/before/home-default.png` | `docs/ui-parity/after/home-default.png` | Validate shell/card hierarchy and CTA icon consistency. |
| `/today` | Workout loaded with at least one exercise card | `docs/ui-parity/before/today-loaded.png` | `docs/ui-parity/after/today-loaded.png` | Validate action row icon consistency and card spacing. |
| `/week` | Generator controls visible | `docs/ui-parity/before/week-controls.png` | `docs/ui-parity/after/week-controls.png` | Validate control hierarchy and generate action treatment. |
| `/checkin` | Weekly review form visible | `docs/ui-parity/before/checkin-form.png` | `docs/ui-parity/after/checkin-form.png` | Validate form control visual consistency and submit action. |
| `/history` | Trend modules visible | `docs/ui-parity/before/history-modules.png` | `docs/ui-parity/after/history-modules.png` | Validate analytics module balance and CTA icon consistency. |
| `/guides` | Program guide cards visible | `docs/ui-parity/before/guides-list.png` | `docs/ui-parity/after/guides-list.png` | Validate card rhythm, type scale, and dock parity. |
| `/settings` | Program override controls visible | `docs/ui-parity/before/settings-program.png` | `docs/ui-parity/after/settings-program.png` | Validate action icon consistency and status readability. |
| `/onboarding` | Account + program + equipment sections visible | `docs/ui-parity/before/onboarding-default.png` | `docs/ui-parity/after/onboarding-default.png` | Validate section hierarchy and segmented controls. |
| `/login` | Login form visible | `docs/ui-parity/before/login-default.png` | `docs/ui-parity/after/login-default.png` | Validate auth form style consistency with shared controls. |
| `/reset-password` | Request + confirm forms visible | `docs/ui-parity/before/reset-password-default.png` | `docs/ui-parity/after/reset-password-default.png` | Validate multi-card auth flow consistency. |

## Review Checklist
- [ ] Typography hierarchy remains consistent across all captured routes.
- [ ] Card/material tiers match expected shell/module/accent usage.
- [ ] Navigation and primary actions use consistent icon style.
- [ ] Spacing rhythm remains stable between before/after captures.
- [ ] No clipped or overflowed controls on mobile baseline viewport.

## Progress Sync (2026-03-06)
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

