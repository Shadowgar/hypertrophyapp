# Existing backlog implementation and qualification — 26 October 2026

Application source: **`252d3dcf92cdc31b7c0f8c15f00dd5cbf04ee70a`**, in existing
[PR #119](https://github.com/Shadowgar/hypertrophyapp/pull/119). Later evidence-only
commits do not change that application tree. Exact final-head CI results and owner
handoff are recorded in the PR conversation and its checks. This supersedes the
current-state conclusions of the [05:42 UTC inventory](../../../audits/2026-10-26-backlog-reconciliation.md),
which remains an unchanged historical snapshot. PR #108 at `33598c3` remains the
approved visual reference; its large static asset collection was not integrated.

## Integration disposition

| Item | Work and disposition | Integration / remaining action |
|---|---|---|
| #120 | Next.js security remediation qualified independently. Owner-authorized head `e8548e7` merged as `a388cb5a4b974f0ef26cb8a13dd107f75cd82dda`. | **Deployed.** API/web versions and image labels agree; protected-main CI40281255906 passed. Release monitor 40282125044 attempt1 timed out while the host continued building; attempt2 passed after host completion. The failed attempt is retained. |
| #119 | Authoritative Home retained; combines original Programs, nullable-profile/history protections, reconciliation, compatible dependencies and the remaining approved UI. | **Combined candidate; not deployed.** Separate owner merge/release authorization is still required. |
| #121 | Exact `e2e02373` is retained in #119 ancestry; distinct read-only program catalog and navigation. | Superseded by the combined candidate; do not merge twice. |
| #122 | Exact `4bf880cd` retained; guarded initialization, truthful nullable targets and original profile/history protections. Its obsolete legacy-Home guard did not replace #119 Home. | Superseded by the combined candidate. |
| #123 | Exact `be8206ca` retained as the dated inventory; this report supplies the actual closeout outcome. | Superseded by the combined candidate and this evidence. |
| #116 | Dependabot closed the broken grouped upgrade after #120. Next remediation is deployed. Zod4.6.7, Vite7.3.7, Vitest/mocker4.1.12, parser7.1.6 and source-map-js1.2.2 are in #119. | Superseded by #120 plus the compatible #119 replacement. Tailwind4 was **not adopted**; installed Tailwind3.4.19 remains compatible and audit-clean. Its optional major migration is deferred, not a patched-vulnerability claim. |
| #124 / #125 | Subsequently opened by Dependabot. pypdf6.21.2 is in #119; compatible npm security fixes replace #125's failing Tailwind4 group. | Superseded by #119's tested replacement. #125's optional Next 16.4.3 is not claimed adopted; candidate remains patched 16.4.1. |
| #103 | Actual Phase1/Phase2/Customized gym, units, recovery and source-preserving load guidance verified below. | **Keep open**: physical iPhone, strict cold-load acceptance and owner-specific historical two-minute/29-set diagnosis remain limited. |
| #105 | Approved guided setup/Home and Atlas execution/Week/History/Analytics, Settings, Check-In, navigation and guides implemented. | **Keep open** through integration and remaining physical/accessibility/performance acceptance. No new design selection is required. |

No other main merge, deployment, schema change, production account operation or
Customized activation change was performed. The sole production change was the
explicitly authorized #120 security release. No new feature PR or roadmap was added.

## Combined verification, with revision boundaries

| Verification | Observed result / scope |
|---|---|
| Full local API including original private Phase1 workbook | **985 passed,114 skipped**. Invocation began at `c97d646`; API/core/program/knowledge runtime trees are unchanged through the final application source. The unchanged two source-fidelity tests were also rerun with the 12 new target-guard cases: **14 passed**. Workbook checksum verified privately; neither bytes nor raw test output are published. |
| Full core | **882 passed**, also independently repeated in current candidate CI. |
| Disposable PostgreSQL | **336 behavior checks passed**: profile/cleanup 22, load/calibration 172, history/correction 35, Customized lifecycle 77, history API9 and current-schema selected dates 21. Plus 12 negative target-guard checks. Current 0026 schema/roles/loopback ports and tmpfs/no-mount targets verified before application imports. |
| Historical schema harness discrepancy | Retained 0021-only rehearsal:17 passed,2 failed because current code needs the 0026 calibration table. Added a strictly guarded 0026 opt-in and reran all 21 selected-date cases unchanged; no assertion/skip weakened and no historical failure relabeled a waiver. |
| Migration preservation | Synthetic 0024→0025→0026 rehearsal passed existing-row digests. Seeded user, original set and explicit preference survive; empty tables are not claimed as nonempty consent coverage. Current-schema PostgreSQL and browser snapshots separately cover active plans/consent/corrections. No migration is added by this candidate. |
| Web | At `eb759a85`:450 tests/67 files, types/lint/build passed. At `905305c`:453/68 in CI. The8e9 CI web job passed 456/68, but an actual-API boolean mismatch was then found. The 252d3dc correction passed 45 affected cases locally and **458/68 in the provider web job**. Types/lint/build passed. Lint has0 errors and7 retained warnings. |
| Provider CI checkpoint | `905305c`: CI40296588776 passed, API988 passed/121 skipped, core 882, web 453, documentation/workflow/build/types/lint green. PR policy excludes private source qualification; it is not presented as a full licensed-fixture run. The 252d3dc web/core and container jobs also pass. Final evidence-head results are in PR #119's checks/closeout comment. |
| Containers/security | Exact 252d3dc native ARM64 qualification passed, artifact 12640781303 digest verified; matching API/web revision labels, native sharp/musl and health/guest checks. CodeQL and GitGuardian status is verified per final head in PR #119. Dependency manifests match the fresh audit-clean lock: npm0 known vulnerabilities; pypdf6.21.2 not yanked/OSV0 matches. Default-main's 21 alerts remain open at this checkpoint; provider closure requires integration and a fresh scan. |

The first combined 6f27 web run failed two outdated Check-In fixtures and one Week
snapshot (432/435 passed). `fe9f0ab` supplied the real history/calendar response
shapes and opened the approved detailed-review disclosure; only the Week snapshot
changed. The corrected full run passed. Original failed attempts remain private;
licensed fixtures and test expectations were not fabricated or weakened.

[Test provenance](qualification.json), [appearance results](appearances.json) and [browser receipts](browsers.json) distinguish the mutation journeys at `eb759a85`,
all-account read-only resumption and theme checks at `905305c`, and final link-only
qualification. Later unrelated styling/navigation changes do not turn earlier
captures into final-revision screenshots. Canonical stored history stayed unchanged
when units were switched lb→kg→lb and during final read-only/account-restart checks.

## Actual browser findings and corrections

| Finding | Correction and evidence |
|---|---|
| Initial Week profile read failure permanently disabled preview with no recovery | `e9e41d9`: explicit profile error/retry, independent calendar lifecycle, retained selected dates and retired-account guard. Three new regressions; final actual 503→retry case and late 401/account-switch case passed. |
| History/Analytics dark legacy surfaces combined with light-theme text | `905305c`: scoped CSS now consumes approved semantic surface/input/border tokens. Original 96 cases retained, including 12 real light failures. Final 48 cases/2,004 sampled text elements:0 contrast/overflow/runtime failures, covering all six appearances in History, Analytics, Today and Customize at 390×844/1440×900. Follow Device passed. Portable real-stylesheet Chromium regression also passed all6 palettes and dynamic token repaint. |
| Authored Today header linked to Customized management | `8e9da4b` then `252d3dc`: Authored links to Week. Actual Customized boolean responses link to the existing program manager; a version-bound link is used only when the actual response supplies a proposal ID. The real browser exposed the initial object-only mock error; absent/false/true/empty-object/ID regressions now pass. Final six actual-API link/click cases passed across both sizes; no writes, page/console errors or failed reads. No backend projection or training policy changed. |
| Implicit favicon request 404 | `9ca6c15`: declare existing WorkoutApp SVG icon. Final 905 browser checks saw icon 200 and no favicon error. Earlier 404 observations are retained. |
| One scheduling-context proxy 500 during browser account-switch testing | Next recorded upstream `ECONNRESET`; API had no exception trace. Eight direct/proxied synthetic read replays passed in 37–82ms and the repeated final browser case passed. Root cause beyond the transient socket reset is unproven; no speculative proxy change. |

The Settings development-capability probe's 403 is **expected** with dev endpoints
false. Existing tests assert this contract and destructive controls stay hidden;
it is distinguished from unexpected request failures. There were no application
page exceptions. Provider review threads were rechecked for all original PRs:0
inline threads. PR119 had0 submitted reviews; draft skips, stale reviews on 120/123
and Copilot quota failures are not represented as final-head code reviews.

Canonical Codex Security export remains blocked by the documented output-parent
permissions limitation. No shared host permissions were changed or repeated broken
exports invoked. CodeQL/GitGuardian and manual boundary review are separate evidence,
not a fabricated sealed scan or security acceptance.

## Approved screen and audit trace

| Screens | Implementation and tested behavior |
|---|---|
| 01–09,71 | `c281a20`/`4d9465d`/`48af37a` and #122: welcome/auth/recovery, distinct program choices, required essentials, optional unknowns, scoped equipment/review. Actual committed/lost setup reply recovered without second POST; returning login preserved profile. Storage failure and preference conflicts have targeted negative cases. |
| 10–11 | Original #119 Home remains authoritative, with honest no-plan/error states and one next step; `6f27d861` corrects weekly metric wording and Analytics destination. |
| 12–15,72 | #121 catalog and `cf32288` Customized presentation/guards. Actual preview→unchecked explicit version consent→accept→activate performed; accepted snapshot remains unchanged through save/correction/undo. |
| 16–19 | `cf32288`/`6f27d861`/`e9e41d9`: local dates, source workload preview, separate activation, acknowledged save retained after failed refresh, exact-occurrence progress and profile retry. Actual failed post-activation read recovered with one activation POST. |
| 20–28,39 | `cec1126` plus retained #111/#112 owner: truthful load/rest/error states, source groups/unchanged dose, known1RM/recent/manual paths with qualified-history precedence. Actual 100lb benchmark→65lb provisional suggestion; lost benchmark response retried exactly, one calibration and0 working receipts. |
| 29–38,40–50,68–69,74 | Existing Atlas/core owners retained: source warm-up, persistent navigation, stationary actual set/RPE/RIR, one effective receipt list, timer, frozen save/correction/undo. Actual before-commit failure and committed/lost correction, other-receipt lock, close/reload/exact retry, undo and 29/29 completion verified. |
| 51–55,76 | `3a88475`/`c97d646`/`905305c`: account/occurrence calendar semantics, complete/partial/scheduled/rest/unknown, effective record detail, units; dedicated Analytics with comparable setup series and accessible table, honest insufficient data. No invented growth/readiness metric. |
| 56–57 | `cf32288`: short optional actual Check-In, acknowledged save and read-only unknown-result reconciliation; one POST after injected lost reply. Detailed review stays mounted after opening/closing and cannot be submitted twice. No durable offline or reload-safe idempotent Check-In write is claimed. |
| 58–64,70,73,75 | `e455632` and #122: scoped training/equipment settings, Auto/null preserved, profile retry; six semantic appearances with explicit save/restore, default Classic Dark, independent device choice and units. Advanced controls retained separately. |
| 65–66 | `eb759a85`: real guide library/phase/day/exercise navigation, source notes/video, truthful missing/error/loading/retry states and stale-account/route protection; source record in disclosure. No unavailable dose/warm-up instruction fabricated. Actual drill-down passed. |
| 67,77–78 | Responsive navigation/More,48px primary controls and visible keyboard focus. Final 18 route/viewport checks and read-only account switch passed. Physical keyboard/Safari/VoiceOver acceptance remains pending. |

All 28 findings remain mapped: **F01/F12/F17/F24** account/setup;
**F02/F15/F26** scoped equipment; **F03/F04/F05/F06/F22/F25/F27** runner/device;
**F07/F10** units/preferences; **F08/F09/F14** completion/calendar/preview;
**F11/F18/F19** Home/navigation/responsiveness; **F13** explicit mode consent;
**F20/F21** History/Analytics; **F23** starting load; **F16** Check-In;
**F28** plain primary-flow language. These are implementation/verification mappings,
not blanket acceptance of every physical-device state.

## Remaining acceptance and owner decision

[All timing samples](performance.json) are retained. Authored fresh-client median
2.612s(n4), resume1.102s(n3); final quiet Customized fresh median1.479s(n3), range
1.472–6.400s, resume1.006s(n3). One final cold sample still missed5s. Earlier
Customized samples were materially worse and remain visible with their shared-host
I/O caveat. Neither later fluctuation nor a favorable median proves the regression
nonexistent. Earlier large-history misses and the original7.353s observation remain
in the [prior bounded investigation](../../today-performance-2026-10-23/closeout-2026-10-24/CLOSEOUT.md).
No new performance architecture or training formula was introduced.

The owner's original two-minute production symptom was not reproduced. Synthetic
source regrouping explains this test occurrence's FullBody1+2/29 sets; it does not
establish the cause of the owner's historical occurrence. Cross-device fresh
contexts retain server receipts, but do not invent a qualified working-load prefill
from manual unknown-setup data; same-context reload draft retention was separately
verified. [Physical iPhone instructions](IPHONE.md) use synthetic nonproduction data.

The owner decision is whether to authorize **this combined PR #119's main merge
and existing automatic release** with these explicit acceptance limits. Component
PRs must not be merged separately as well. Keep #103/#105 open. Production backup,
schema/configuration verification, rollback boundaries and any future migration
remain under the established release procedure; this candidate adds no migration.

## Representative actual application captures

These are synthetic browser captures, not replacement design alternatives.

| Capture | Revision |
|---|---|
| [Mobile starting estimate](assets/mobile-estimate.png) / [saved set and rest](assets/mobile-first-saved-rest.png) | eb759a85 |
| [Desktop uncertain correction](assets/desktop-correction-uncertain.png) / [completed History](assets/desktop-complete-history.png) | eb759a85 |
| [Light History](assets/classic-light-history.png) / [light working set](assets/classic-light-today.png) | 905305c |
| [Light Analytics](assets/classic-light-analytics.png) | 905305c |
