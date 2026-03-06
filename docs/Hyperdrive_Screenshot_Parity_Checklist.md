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
- Repository state synchronized through commit `1026d25` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `63 passed`
  - Web tests: `16 passed`
  - Web build: success
- Additional progress after previous sync:
  - `777cb86`: pruned obsolete visual-route snapshots (`apps/web/tests/__snapshots__/visual.routes.snapshot.test.tsx.snap`)
  - `739cb99`: migrated API startup from `@app.on_event("startup")` to FastAPI lifespan in `apps/api/app/main.py`
  - `18dd81b`: replaced model `datetime.utcnow()` defaults with centralized UTC helper in `apps/api/app/models.py`
  - `cb317d0`: hardened `scripts/mini_validate.sh` with compose command detection and one-shot rebuild/retry fallback for failed containerized API test runs
  - `3596622`: migrated auth stack from `passlib/python-jose` to `bcrypt/PyJWT` in API runtime paths
  - `1026d25`: added coach-preview API edge-case tests for invalid template handling, low-readiness deload extension, and phase-transition boundary branches
- Current warning profile:
  - FastAPI startup deprecation warning removed.
  - SQLAlchemy `datetime.utcnow()` warning class removed from API test runs.
  - `passlib` and `python-jose` deprecation warnings removed from validation output.
  - `mini_validate` run now reports clean test results without warning spam in the default path.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

