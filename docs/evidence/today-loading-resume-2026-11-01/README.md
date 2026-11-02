# Today loading and reliable resume

Issue #103, related #105. Starting protected main `06e910896203355c11815d3e586e1dec6d8e0c3e` passed CI [41361759667](https://github.com/Shadowgar/hypertrophyapp/actions/runs/41361759667), including complete API/private source-fidelity qualification, and CodeQL [41361759384](https://github.com/Shadowgar/hypertrophyapp/actions/runs/41361759384). Its release workflow was skipped. No main correction was required.

## Investigation and change

Reused the [October performance investigation](../today-performance-2026-10-23/README.md) and [96-navigation closeout](../today-performance-2026-10-23/closeout-2026-10-24/CLOSEOUT.md). Those already qualified request-local Authored batching and identified host/cache variation; their cold-start research was not repeated. The current baseline does not literally render “No workout loaded.” This package reproduces avoidable waiting and failure/retry behavior rather than claiming that old string is present.

Fresh real API/browser traces showed Today waiting for a diagnostic health ping and an auxiliary progress projection before first-use entry. Same-day soreness **Skip** then fetched Today, profile and progress again even though it wrote no recovery evidence. The candidate removes the health prerequisite, starts progress independently and retains the verified same-day workout after Skip. Skip still rechecks the authoritative local date; saving soreness still refreshes the workout/constraints.

The independent branch review found a stale progress-failure status after a newer set receipt; its regression failed before the correction and passed afterward with all154 focused tests. Counts/receipts keep their generation guard, while the current read status settles independently.

Selected GETs have a 15-second deadline and an explicit retry state. No mutation receives an automatic timeout or retry. A failed mandatory training lookup does not imply calendar mode. Date errors identify date verification; Flexible workout-read failures are visible; optional progress failures keep the verified Today counts rather than displaying an empty workout.

Transient refresh failure preserves the same account/occurrence draft in memory, with the retained runner hidden and disabled until server revalidation. Definitive absence, changed occurrence, account changes and existing mandatory gates retire old authority. Existing persisted drafts and original command recovery handle full reloads. This adds no offline logging, cached prescription authority or alternate saved-set system.

## Measured before and after

[Measurements and individual samples](measurements.json). Each cell has three visits per production build, using Chromium at 390×844 against the real isolated API/PostgreSQL. “Usable” means navigate to Today, explicitly Skip optional soreness, open the same exercise, enter an actual load/reps and reach an enabled Save Set. No set was submitted by the timing driver.

| Scenario | Baseline usable median (range), ms | Candidate usable median (range), ms |
|---|---:|---:|
| Authored Phase 1 | 2103 (1585–2535) | 1467 (1246–1982) |
| Authored Phase 2 | 1983 (1493–2091) | 1554 (1437–1567) |
| Native Flexible | 2356 (2307–2562) | 1914 (1398–2436) |
| Consented Customized | 1181 (890–1739) | 893 (738–4669) |
| Phase 1, real progress response held +1500 ms | 3875 | 1499 |
| Phase 1, real health response held +1500 ms | 3590 | 1622 |

First-use request budget changes from **two Today/progress/profile reads to one each**, and one diagnostic health read to zero. Both required date checks remain. Training mode, soreness and appearance preference reads remain. Baseline/candidate builds ran sequentially on a shared host; browser/cache/process-cold state was not experimentally controlled. The 4669 ms candidate Customized sample is retained, not discarded. The timing and real-browser build uses source `56b90429feb34d5c7251531cf1bb2a5b7585e8c3`; the final followup changes only that failed-progress status branch and is separately regression-tested. These small samples establish an observed median improvement and the removed dependency, not a p95, a universal two-second SLA or an iPhone performance claim.

The comparison crossed UTC midnight. The existing external routing-clock technique kept November 1 fixtures consistent for candidate timing; authentication/JWT time stayed actual. Session identity, exercise projections and estimate traces were verified identical before timing. The recovery run used actual application clocks and separate fresh Monday fixtures. No production clock/configuration changed.

## Qualification and preservation

- [Browser results](browser-results.json): real slow Today response, 15-second mandatory-mode timeout without calendar fallback, offline reload/draft retry, committed lost-response exact retry followed by receipt-based reload, precommit interruption/full-reload exact retry, one receipt per command, canonical kg, correction/undo, account switching, 390×844 and desktop containment. Save Set position/scroll remained stable across confirmed retry. No page runtime errors occurred.
- [Database comparison](database-results.json): all ten original measurement/recovery fixture source projections preserved; owned audit receipts and canonical kg checked. The four timing-mode accounts received no workout writes. Earlier failed harness attempts retained their synthetic records; none was reset or deleted.
- [Source parity](source-parity.json): all eight compiler inputs, nine Phase 1/2 artifact files and the three PR #137 runner/calibration/composer files remain byte-identical to main. Compiler SHA-256 stays `e258c5e512fb00b8a550510f4fac507486001146fa425e8856f41046aef8a7d4`. This is byte parity; final licensed qualification belongs to normal CI.
- [Qualification metadata](qualification.json) records local focused checks, immutable review scope and source hashes. Normal CI, CodeQL and GitGuardian must qualify the final PR head. No local full application suite was repeated.

Environment: new PostgreSQL16 Linux/ARM64 container `ferravis-today-loading-disposable-20261101`, image `sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e`, loopback55443, database `today_loading_browser`, role `today_loading_test`, 384 MiB tmpfs, 512 MiB memory limit, no mounts. Container/role/database identities were verified before isolated fresh-schema bootstrap. Next loopback3043 and API8043 used explicit isolated configuration. No migration or production target was used.

Test-harness corrections before the passing recovery run: remove Home background requests from the timeout counter; distinguish authoritative receipt recognition on reload from an unresolved command; use UTC fixture dates consistently after midnight. Failed synthetic evidence stays private. Cached WebKit2248 could not launch because host dependencies are missing; no host package installation was performed.

## Reproduction and iPhone acceptance

The retained [timing driver](measure.cjs), [recovery driver](recovery.cjs), [guarded measurement API](serve.py), [fixture seed](seed.py), [fresh recovery seed](seed-recovery.py) and [preservation collector](collect-evidence.py) require the explicit disposable target above. Run from the worktree root with an isolated environment, absolute candidate program/knowledge/PYTHONPATH settings, disposable-only JWT key and fresh private `.qualification` account files. Never inherit database defaults. `PLAYWRIGHT_MODULE`/`CHROMIUM_EXECUTABLE` select installed local tools. Seed the November 1 timing fixtures with `TODAY_FIXTURE_DAY=2026-11-01` and `TODAY_FIXTURE_INSTANT=2026-11-01T23:45:00+00:00`; run the external timing API with `TODAY_FIXTURE_CLOCK=1`. Recovery uses actual clocks and fresh current-week UTC fixtures. Synthetic credentials, tokens and raw service logs are not committed. The current preservation receipt includes one synthetic committed row from an earlier failed harness attempt; its collector explicitly uses `TODAY_EXPECT_OLD_MANUAL_RECEIPT=1`. A clean reproduction defaults to zero for that unused timing fixture.

On a separately authorized isolated review build with synthetic accounts, use physical iPhone Safari:

1. Open Today in Phase 1, Phase 2, Flexible and a consented Customized plan. Check the loading text, Skip once, then reach the existing starting-weight choices and stable set entry. Record actual navigation-to-entry times.
2. Disable connectivity during a read, restore it and retry. Verify the original draft returns only after verification; a rest day must come from an authoritative response. Repeat with a failed training-state lookup.
3. Interrupt a save before and after server receipt, reload, and resume. Confirm one saved record, original load/unit/command, no duplicated set and unchanged source identity. Correct and undo, then reload again.
4. Keep the keyboard open during Save Set, background/restore Safari, and switch synthetic accounts. Check focus/scroll, pending recovery, no private draft leakage, actual-date Flexible continuation and source/consent restrictions.

Physical Safari keyboard, tab suspension, touch and gym-network behavior remain unaccepted. Keep #103 and #105 open. Nothing in this package authorizes deployment, production writes, schema changes, account resets, merging or release-control changes.
