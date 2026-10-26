# Onboarding integrity qualification

Candidate base: `ad789ff983a51c2445fde34c849d3738fcb0311a`. Scope and behavioral authority: [bounded plan](../../plans/truthful-onboarding-2026-10-26.md). All data in verification is synthetic; no production account, service, configuration or record was changed.

## Reproduced defects

- Original frontend produced 12 failures / 19 passes against the new registration/Today/date tests: fabricated profile/review writes, automatic legacy plan work, failure retry and weekly-review blocking.
- Original normal profile/program-switch implementation failed all three corrected history-preservation cases (program preference, changed answers with no set logs, confirmed program switch). Each compared full retained plan/check-in/set rows. The first draft fixture was missing the required plan phase; that harness error was corrected before the three deletion failures were recorded.
- A fresh profile returned maintenance/zero nutrition and rejected omitted targets. Existing API/core expectations for those values are revised explicitly to unknown/null, not waived.
- Independent review found reload recovery and delayed error-body account-switch gaps. Both were reproduced with new tests before repair. The guarded initialization route was absent in the two initial-setup regression checks before implementation.

## Qualification

| Check | Result and scope |
|---|---|
| Focused real PostgreSQL/API/core | **168 passed**. Purpose-labelled disposable PostgreSQL 16.13, loopback ephemeral port, dedicated synthetic role/database, tmpfs only and no mounted production paths. Includes full-row plan/check-in/set preservation, target omission, setup locks, concurrent preference saves and unchanged dev-wipe safeguards. |
| Full core suite | **873 passed**. No numerical training or source-prescription changes. |
| Full frontend | **328 passed / 52 files** after the shell integration fix; five additional-boundary cases are included in that count. |
| Types, production build, lint | Production build/typecheck passed. Lint: **0 errors, 7 existing hook-dependency warnings** outside this package. Local web rewrites were verified against isolated API 8129; no inherited production API/database environment. |
| Earlier PR CI, `ba65ece4` | API **971 passed, 121 skipped**; core/web/CodeQL/GitGuardian passed. This precedes the final shell correction and is not final-head acceptance. Latest exact-head results are recorded in PR #122. The PR profile intentionally excludes the two private-workbook source tests; full protected-main release qualification remains separate. |
| Independent review | Reload setup and delayed error-body race findings were reproduced and fixed. A further real-browser discovery—shell remount at own registration—was reproduced by three failing shell integration tests, repaired, and reviewed again. Final review found no remaining concrete account-isolation issue in the reviewed code; it is not a canonical sealed security scan. |

### Actual browser journeys

Production-built frontend at loopback 3129 and actual API at 8129 used the separately verified `synthetic_onboarding_browser` database. No production origin, account or record was used. Browser checkpoints:

1. Mobile full questionnaire → real registration → injected503 before profile commit. Blank server profile retained unknown nutrition and allowed explicit recovery.
2. Reload → **Continue account setup** → server check → private height/weight/date inputs re-entered; no credentials re-entered or second registration.
3. Enter only calorie/protein targets → real server commit → deliberately drop response → visible retry/error → reload → read saved choice → Week. Stored calories 2400/protein 140; phase/fat/carbs remained null. No duplicate setup write on recovery.
4. Failed Week preview showed retry and no activation control. Actual retry produced a preview without persistence. Explicit activation created exactly one plan; Today opened Cross-Body Lat Pull-Around with weight/reps/Save controls and no weekly-review request. Skipping the optional soreness prompt created no soreness report. No weekly reviews, weekly check-ins or performed sets were fabricated.
5. Separate fresh Auto and Customized accounts reached `/week` and `/customize` respectively. Each issued only registration and guarded setup POSTs. Auto stayed null-program/auto; Customized stayed explicit manual/full_body_v1 and did not consent/activate a program. All five nutrition fields remained null.
6. Rendered nutrition inputs, keyboard focus and overflow were checked in all six appearances at 390×844 and 1440×900. Preferences started Classic Dark/lb; changing appearance in this synthetic account was explicit. Rendered input text contrast ranged 12.31:1–17.93:1, keyboard focus had a 3px outline, and all 12 states had no horizontal overflow; transitions were suppressed for settled color readings. Rendered measurements are retained in [appearance checks](appearance-checks.json).

7. A new browser context signed into the established synthetic account through onboarding. Its only POST was `/auth/login`; the chosen kg preference, Classic Dark appearance, explicit targets and scheduled Authored program were retained. No runtime exception occurred.

The final startup handoff fix is covered by real-shell tests for own registration success/failure, another account, logout and cross-tab switch while a save is pending. Fresh Auto/Customized registration handoffs and Authored setup recovery were rechecked after the fix. An already-issued request can still complete for its original authenticated account; stale UI and writes to a different account are rejected. This is not a promise to cancel a server transaction.

### Intermediate failures retained

The first full frontend run found two unit-preference tests relying on a fabricated default adherence score. They now explicitly report a score while retaining canonical-weight/unit-switch assertions; the affected six tests and full 328-test suite pass. An earlier SQLite run had 161 passes/1skip/1 obsolete pre-onboarding nutrition-default failure; the corrected expectation passes in final PostgreSQL and API CI. An initial shell-test typecheck used Playwright's `exact` option with Testing Library; the harness was corrected before the passing build. Browser harness attempts also corrected case-sensitive labels, an empty Next route-announcer mistaken for the error alert, and inaccurate Week/navigation landmark names. Those attempts are not counted as product passes. The before-commit failure exposed the actual shell-remount defect, which was fixed rather than dismissed as harness noise.

### Visual evidence

- [Mobile explicit targets](mobile-explicit-targets.png)
- [Mobile lost-response recovery](mobile-lost-response.png)
- [Desktop first workout](desktop-first-workout.png)
- [Desktop optional targets](desktop-targets-classic-dark.png)

## Reproduction boundaries

Use an isolated checkout and explicitly verified disposable `DATABASE_URL`/`TEST_DATABASE_URL`; follow `DB_SAFETY_LOCK.md` before test helpers or application bootstrap. Run `apps/api/tests/test_truthful_onboarding.py`, existing profile protection/schema/state/program-selection/dev-wipe modules and `packages/core-engine/tests/test_intelligence.py` on PostgreSQL for the focused qualification. Run all `packages/core-engine/tests`, then web `vitest run --maxWorkers=1`, lint, typecheck and production build. Use synthetic accounts only for the browser sequence above, intercepting only the intended failure/lost response; normal endpoints must reach the disposable API. Never use a production workbook, account or database as a browser fixture.

## Limits

The application retains the approved runner and deterministic planning owners. It does not retrospectively identify/correct previous fabricated nutrition/review records. Full onboarding visual completion, physical iPhone keyboard/background acceptance, the original unreproduced two-minute symptom and the separate blocked canonical security export are not established by these checks. Nothing in this PR has been deployed.
