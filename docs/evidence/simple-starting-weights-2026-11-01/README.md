# Simple starting weights: bounded implementation and qualification

Owner-authorized gym-use package for [#103](https://github.com/Shadowgar/hypertrophyapp/issues/103), PERS-002/PERS-008 and the approved unified UX under [#105](https://github.com/Shadowgar/hypertrophyapp/issues/105). Base: `88bb339fc820e59973fc20666ea00423f43f73fa`. Both issues remain open. This is implementation evidence, not production/device acceptance.

## Delivered behavior and owners

The three optional first-use choices now sit immediately below the stationary working-set composer: known 1RM, recent weight/repetitions and manual actual load. Authored reports reuse `AuthoredCalibration` and the existing account/occurrence/setup-scoped initial-calibration API. Equipment identity, setup and attainable loads are disclosed in an expandable section only for a requested estimate. They remain mandatory evidence for that estimate; safe manual logging does not require the benchmark form. Source conflict/technique, consent, pending-write and recovery gates remain in force.

`core_engine.load_intelligence.decide_initial_working_load` retains the [approved initial-only policy](../../contracts/proposals/authored-starting-load-v1.md). The browser adds no load calculation. Estimates remain labeled provisional; current work and comparable completed history take precedence. Source sets, reps, effort, rest, techniques and occurrence identities remain unchanged beside editable actual values. Unsupported targets, first-set techniques, bodyweight/assistance and insufficient setup/evidence retain abstention and manual entry when otherwise permitted. No maximum test is requested.

Saved lb/kg preferences drive presentation, with lb as the existing default. Benchmark drafts retain original magnitudes/units; an untouched value never passes through rounded display text on save. Benchmark and equipment units are independent declarations. Equipment fields retain their labeled unit even when working-load display preferences change; changing the equipment unit explicitly clears only that draft grid/list for re-entry. Untouched declarations never get converted through a binary-float grid. Lists retain exact entries when appended or reordered. Pending benchmark and actual-set commands retain exact payloads on retry/reload. `useAtlasSet` remains the canonical-kg actual-draft and receipt authority; no second saved-set store was introduced.

Customized displays the same choices but explicitly explains that self-reported max/recent-set information has no approved conversion into a new starting recommendation in its independent policy. Its existing equipment/strength setup and consent flow remain accessible; actual manual logging and comparable performed-evidence guidance are unchanged. No Authored formula was activated for Customized.

Browser qualification exposed a first-save layout defect: training-state refresh temporarily inserted 24 px above the runner, while removing expanded help shortened the document and forced scrolling. The controller remains mounted and validated, with its summary hidden during active exercise entry. Mandatory blocked/resume decisions still retire the runner and reveal the resolution view. Help already offered stays mounted/read-only through the occurrence so Save Set and the focused input stay stationary. A pending benchmark can still retry its original command after actual work or a reload; the server re-evaluates current evidence rather than reviving an old estimate.

## Changed-file review

- `apps/web/components/atlas-runner.tsx`: inline help, Customized policy disclosure and persistent session layout; source rendering/composer command owner unchanged.
- `apps/web/components/authored-calibration.tsx`: three choices, progressive evidence collection, unit-safe report presentation and retained retries.
- `apps/web/app/today/page.tsx`: hide only the mounted training summary during exercise entry; server decision callbacks and mandatory retirement unchanged.
- `apps/web/tests/starting-load.test.tsx`, `apps/web/tests/today.flexible.test.tsx`, the one-line Today snapshot, and focused API/core calibration tests: focused behavior and negative regressions.
- Plan and this evidence directory: implementation scope, captures and sanitized results only.

Fresh independent review at `eb0f95e42e177e418cba0ec36470fd138776e213` identified one Important converted-list precision issue. Its regression failed before the fix and passed afterward; additional reorder coverage also failed before its correction. The GitHub automated review subsequently identified two additional edge cases: mixed-unit grid conversion could change the selected step, and confirming a restored pending benchmark after actual work could hide the panel. Both have focused red/green regressions; original benchmark/equipment declarations now stay independent, and restored pending commands initialize the persistent help state. Core cases pin 90 lb on a 5 lb grid to 60 lb, and 100 lb with an unchanged 5/5/15 kg grid to 15 kg. No deferred minors remain. The subsequent browser-discovered layout correction has focused red/green tests, including mandatory-blocker retirement, and real browser geometry measurements. A layout-only mocked-API regression also verifies every expanded benchmark control stays inside the card content at 390 px. No backend runtime, migration, compiler, artifact, authentication, SMTP or release-configuration files changed. Paired non-private API/core regressions document the unchanged owner’s exact-unit floor.

## Verification

- Focused web: 93 passed across starting-load, Atlas set composer, Today load intelligence, Customized calibration, appearance/provider and Flexible Today suites. New inline-path regression run initially had 10 failures before implementation. The two layout regressions separately failed before correction.
- Focused existing API/core: 212 passed, 2 PostgreSQL-only concurrency cases skipped on fresh, explicitly guarded SQLite. Initial collection attempts lacking required disposable-root markers were rejected and corrected. These skips are not PostgreSQL race qualification.
- TypeScript and changed-file ESLint: final result recorded with the PR checks. The first normal CI run passed 609/610 web tests and failed only the intentional summary-wrapper snapshot; its reviewed one-line expectation was updated, then the final head received fresh qualification.
- [Browser results](browser-results.json): real local API and temporary PostgreSQL 16, not mocked responses; desktop 1440×900 captures and 390×844 Chromium execution. Known/recent/manual paths, exact benchmark retry after a committed lost response and reload, exact actual-set retry, correction/undo/reload, preferred-unit reload, account switching, source-technique/manual fallback, and stationary composer are asserted. First Phase 2 Today exercise appropriately rejects a provisional estimate because its first-set technique is not ordinary; the tester acknowledges that technique before manual logging.
- [Database comparison](database-results.json): original source projections preserved for all seven exercised/cold accounts; logical receipt counts, account/occurrence ownership, calibration command uniqueness and canonical kg values verified. Native Flexible retains its actual execution context and per-set local dates. Calendar receipts retain their existing timestamps/scheduled lineage; their per-set Flexible date fields stay unknown, with no fabricated backfill. Accounts/programs were synthetic; all calendar plans were generated through the normal selected-date API. Flexible enrollment/start and Customized challenge/consent/activation used their real server contracts.
- [Compiler/artifact parity](compiler-parity.json): all eight compiler inputs and nine Phase 1/2 JSON files byte-identical to the qualified base. Compiler fingerprint remains `e258c5e512fb00b8a550510f4fac507486001146fa425e8856f41046aef8a7d4`. This is byte parity, not a rerun of licensed-source qualification.

Environment: isolated worktree, Next loopback3041, API loopback8041, PostgreSQL loopback55441; database `gym_start_browser`, role `gym_start_test`, image `sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e`. PostgreSQL used a new 384 MiB tmpfs, 512 MiB memory limit and no mounts, independently verified before fresh-schema bootstrap. No migration or production connection was run. Earlier fixture/harness attempts (missing fixture fields, invalid single-date calendar, reserved test email domain, select-label mismatch) were corrected before the recorded passing run; failed evidence remains private. No production accounts, configuration, containers or release controls were changed.

## Before and after

Before captures use exact-base AtlasRunner/AuthoredCalibration components with the same valid source exercise; no baseline benchmark was submitted. After captures use the candidate UI and synthetic accounts.

| Before | After |
|---|---|
| [Mobile entry](before-mobile-entry.png) | [Mobile inline choices](after-mobile-entry.png) |
| [Technical benchmark sheet](before-mobile-benchmark-sheet.png) | [Inline benchmark and expandable setup](after-mobile-benchmark.png) |
| | [Desktop provisional estimate](after-desktop-estimate.png) |
| | [Mobile saved-set state](after-mobile-saved-set.png) |
| | [Phase 2 manual boundary](after-mobile-phase2.png) |
| | [Flexible native occurrence](after-mobile-flexible.png) |
| | [Customized boundary](after-mobile-customized.png) |
| | [Expanded benchmark card containment](mobile-expanded-layout.png), layout-only mocked API regression at 390 px |

## Remaining acceptance and physical iPhone steps

Use an isolated review build with synthetic accounts, not current production. On Safari at normal text size and with the software keyboard:

1. Open an Authored Phase 1 exercise in lb, review source reps/effort/rest, choose each path, and enter the first actual set. For an estimate, provide a real same-setup benchmark and real attainable loads; an estimate is not a guarantee of effort or suitability.
2. Keep reps focused, tap Save Set, and confirm keyboard/focus, scroll, Save Set position, one receipt and next-set entry remain stable. Background/restore the tab, interrupt/retry a save, correct and undo a set; confirm no duplicate work.
3. Change to kg, reload and switch synthetic accounts. Verify physical loads remain unchanged and no draft/report leaks to another account. Review converted equipment list edits without losing original precision.
4. Repeat with Phase 2 techniques and unsupported targets, native Flexible across actual local days, and an explicitly consented Customized plan. Confirm manual entry stays available only when the existing source/consent/recovery gates permit it.

Chromium's mobile viewport and DOM focus assertions do not qualify iOS Safari keyboard, touch ergonomics, standalone/PWA behavior, background suspension or real equipment usability. No training-outcome accuracy, new numerical policy, physical iPhone acceptance or production deployment is claimed. Keep #103/#105 open until owner gym acceptance. Production remains separately authorized.
