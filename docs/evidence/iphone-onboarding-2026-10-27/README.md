# iPhone onboarding and first scheduling repair

Owner-authorized bounded implementation, Issues #105/#103; base
`d905397d8def962077384781501072dbf669786c`. No merge, deployment, production data
or release-control writes. Approved unified UI and existing backend decision owners.

## Plan and checkpoint

- Reproduce and protect both password forms, browser navigation, reload/re-login,
  blank/saved/established continuation, safe setup review/edit and date preview.
- Keep guarded first initialization, explicit Customized consent, exact program/
  dates/account/revision boundaries. Preview never activates.
- Test regressions before corrections; use verified disposable PostgreSQL and
  synthetic browser accounts. Final candidate: full web checks, applicable API,
  browser desktop/mobile WebKit, scoped Codex Security and immutable-head CI.
- One focused PR related to #105; keep #103/#105 open; stop before merge/deploy.

The earlier temporary worktree disappeared between turns. Its uncommitted changes
and logs are unavailable. This recovery uses the persistent worktree
`/home/rocco/hypertrophyapp-worktrees/iphone-onboarding`, branch
`fix/iphone-onboarding-scheduling`; no earlier results qualify the recovered patch.
Commit checkpoints during recovery. Next: recover failing regressions, implement
and verify the bounded corrections, then complete final qualification and PR.

Read-only live baseline on 2026-10-27: main d905397, public API/web 891228f,
publisher false. Timer was observed active, differing from the earlier inactive
observation; neither control was changed. Production checkout debug log is
pre-existing modified runtime work and is untouched.

## Corrected behavior and reproduced causes

| Defect | Verified cause / resulting behavior | Changed runtime files |
| --- | --- | --- |
| Password visibility | Baseline Chromium toggled type correctly. Mobile WebKit dropped the focused input when its type changed. The shared control retains the live autofill value and restores focus after the DOM update; explicit hidden/visible text, pressed state and control association make the result clear. | `apps/web/components/password-field.tsx`, `apps/web/app/login/page.tsx`, `apps/web/app/onboarding/page.tsx` |
| Back after registration | Setup stage was component-only; a remount exposed the welcome/account experience despite a retained token. Authenticated entry reads server eligibility, registration replaces its account-step history entry, and subsequent Back/Forward is guarded and account-aware. | `apps/web/app/onboarding/page.tsx`, `apps/web/app/onboarding/setup-draft.ts` |
| Re-login loses position | Login used only a return path and ignored saved setup state. The profile API now derives a read-only `setup_status` from raw first-setup eligibility and account-owned retained plans/receipts. Initial accounts resume setup; saved unscheduled accounts reach Week or explicit Customized planning; established accounts keep their safe requested destination. | `apps/api/app/routers/profile.py`, `apps/api/app/schemas.py`, `apps/web/lib/setup-continuation.ts`, `apps/web/lib/api.ts`, login/onboarding pages |
| Preview appears inert | Disabled conditions were poorly explained, `makeRequest`/stale paths could return silently, equivalent focus refreshes invalidated responses by request counter, and status was remote from controls. Explanations, immediate pending, obvious read-only success and retry are now local. Identity/program/week/timezone/revision changes still invalidate results. Manual/null preferences have a distinct placeholder and can explicitly choose/save Auto; Customized aliases retain separate consent. | `apps/web/app/week/page.tsx` |
| No safe setup access | Home/Settings lacked an obvious continuation/review entry. They now expose Resume Setup / Review/Edit Setup. Saved answers are read from the account; an explicit authenticated PATCH edits only current name/age/weight. Equipment/preferences and program/dates use their existing separate edit flows. | Home/Settings pages, `apps/web/components/saved-setup.tsx`, profile router/API client |

The existing `profile._initial_setup_available`, profile mutation owners and
account lock retain initialization authority. `profile._has_training_history`
performs read-only classification, including older plans and retained receipts.
Frontend continuation is navigation only. Existing selected-date endpoints own
exact dates/program identity, preview digests and placement revision validation;
Customized lifecycle still owns consent and activation. No prescription,
GenerationProfile mapping, numerical policy, schema or migration changed.

Two additional lifecycle failures were independently identified and reproduced:
StrictMode cleanup stranded onboarding's submitting latch, and replayed login
reads redirected twice. Browser qualification also observed interrupted catalog
reads before the request guard was added. Cleanup retires obsolete
requests, releases the setup latch, and gates login navigation/pending cleanup by
request and mount revision. Their failing regressions now pass. Manual/null Auto
selection was also independently reviewed and verified by an actual save command.

## Qualification record

Runtime source revision: `2784f41479220c1a5755ce9febf2aaef8de94bcb`.
Subsequent changes to this evidence package do not change runtime source.

- Full local frontend suite: **508 tests / 73 files passed** at the preceding
  candidate; after the final login revision guard, **59 affected account tests**
  and TypeScript passed. Final-head provider results are recorded on PR #127.
- Focused Week corrections: initial recovery **48/48**, with subsequent alias,
  Manual/null selection/save and lifecycle regressions passing their focused runs.
- Saved basics: **6 frontend cases**, **13 disposable PostgreSQL API cases**.
  Includes authentication, blank-account rejection, validation/unrelated fields,
  history/consent preservation, units, duplicate submits, errors/retry and delayed
  account changes. No reset/drop/truncate or development wipe helper was used.
- Lint: no errors; seven existing hook warnings in unchanged appearance/technique/
  set-entry files. Types pass. The provider web build passed at `15a6444`;
  applicable immutable final-head CI/build/security results belong on the PR.
- [Repeatable browser runner](../../../apps/web/tests/onboarding.first-schedule.browser.cjs):
  desktop Chromium **1440×900** and Linux WebKit iPhone 13 emulation **390×844**,
  Playwright **1.58.2**, `America/New_York`, dedicated loopback web/API ports.
  Both completed registration → program choice → browser Back/Forward → reload
  → close → login → resumed choice → Authored Phase 1 → save profile → two-date
  preview → logout/login → planning → saved setup review.
- [Recorded mutation summary](browser/summary.json): each account registered once,
  initialized once, authenticated twice and previewed once. **Zero activation
  requests and zero page errors.** Direct read-only PostgreSQL verification found
  **zero saved plans and zero set logs** for the browser-account cohort.
- [Rendered mobile preview](browser/mobile-preview.png) visibly offers activation
  separately and labels the preview as not activated. 0/1/2/3/5/6 dates, missing
  prerequisites, failure/retry/slow responses, equivalent focus refreshes, changed
  account/program/week/revision and stale input edits have component coverage.
- Harness-only failures are retained in the external evidence directory: competing
  forced login navigation and closing/navigating pages with in-flight reads caused
  canceled-resource reports in WebKit. The final runner follows the app's redirect
  and waits for intentional read completion; it retains strict page-error checks.

Disposable target: `workoutapp-iphone-1027-pg`, loopback 55429, database
`iphone_onboarding_disposable`, role `iphone_test`, tmpfs data and no production
mounts. Identity was verified before persistence operations. API/web used dedicated
55430/55431. No production environment/credentials/data were copied. WebKit's
missing libraries were extracted in isolated evidence storage, without installing
host packages. Browser automation does not substitute for physical iPhone Safari.

## Security limitation and pending approval

Codex Security capability preflight returned ready; Daybreak Blue access is granted.
Scan `44f4ae2c-c783-44dc-9dc8-293c5d69224f` was started for immutable
`d905397..30331df`. Canonical draft storage was rejected because five owner-owned
ancestor directories under `~/.codex` have mode 775. The proposed correction is
775→755 for exactly `.codex`, `state`, `state/plugins`,
`state/plugins/codex-security`, and its `scans` directory. Explicit permission was
requested; **no permission change, sealed scan or clean scan result is claimed**.
The running scan is preserved for continuation. A final-head scan or supplemental
review remains required once storage is available. Provider CodeQL and GitGuardian
results are separately revision-scoped and recorded on the PR.

No merge, production migration, deployment, publishing enablement, timer restart,
account reset or live-data mutation occurred. The timer was observed active on
resume; publisher false and public API/web 891228f were left unchanged. Issues
#103/#105 stay open and physical-device acceptance remains pending.

## Physical iPhone retest after a separately authorized deployment

1. Use the owner's **existing newly created account**; do not register/reset it.
   Toggle Show/Hide on login and confirm the password changes visibility, retains
   its value and keeps focus. Sign in and check the account-specific destination.
2. If setup is unfinished, use Resume Setup. Test in-app Back, browser Back/Forward,
   refresh, then close/reopen and log in. Registration must not reappear. Unsaved
   private measurements intentionally require re-entry; non-private choices and
   the appropriate step are recovered where available.
3. If the profile is saved, Review/Edit Setup should show saved answers. Explicit
   Save basics changes only current name/age/weight; use the separate Settings and
   program/date links for other changes. Existing workouts/consent stay intact.
4. In Week, check the nearby explanation with 0 or 1 date; choose 2–5 dates and tap
   Preview selected dates. Confirm immediate checking, visible "Preview ready ·
   not activated", sessions and a separate Activate button. Do not activate until
   deliberately ready. Customized continues through its separate consent flow.

Current live 891228f does not include these candidate fixes. No deployment is
implied by this retest procedure or by an implementation/CI result.
