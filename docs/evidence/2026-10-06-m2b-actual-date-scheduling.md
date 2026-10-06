# M1-C deployment and M2B-1 actual-date scheduling qualification

Date: 2026-10-06. Operator: Codex under the attached owner task. Base/main: `ddc75b781cbec9463172e8075faff58c499848f7`. Implementation and review fixes are on `m2b/actual-date-scheduling`, [PR #76](https://github.com/Shadowgar/hypertrophyapp/pull/76). Git records the final source revision; this report does not grant owner acceptance, migration, merge or deployment authority. ADR-007 remains Proposed.

## M1-C deployment

Production checkout already equals current main. Running API/web images are `hypertrophyapp-api:m1c-ddc75b7` and `hypertrophyapp-web:m1c-ddc75b7`; no rebuild/restart or migration was needed. Public `/api/health` and container `/health` return status `ok`, version `ddc75b7`. Read-only deployed-source comparison matched all 134 tracked API/core/program/importer/runtime-rule/compiled-knowledge/copied-web-library files with main, zero mismatches. This comparison does not inspect production records or certify every compiled web asset.

Public home and protected Today/Week/history browser navigation were checked at desktop 1440×900 and mobile 390×844. Protected routes reached login without creating a real-user session or synthetic production history. Authenticated live authored content is not claimed: Phase 1/2 paths were instead qualified by all 13 `test_authored_relationship_fidelity.py` cases on guarded isolated main source, covering native/compressed placement, order, relationships, typed prescriptions and constraints. The smoke SQLite remained empty. An initial browser tool summary contained an unclassified console error/telemetry abort; this is not represented as an entirely error-free historical browser run.

The pre-existing `logs/app-debug.log` modification was preserved byte-for-byte: SHA-256 `e920b78d4b45854dbbc14579574b9195205c6a5bbad4684ee2bad13398001f22` before/after. No production configuration, persistence or unrelated service was changed.

## Model and decision ownership

The user selects 2–5 distinct local calendar dates in the current Monday–Sunday week and explicitly confirms an IANA timezone. Invalid/duplicate/out-of-week/unsupported inputs reject, without hidden correction. Past dates within that week are explicit placements with a warning; they never create performed history. There is no manufactured UTC workout time. A nullable persisted user timezone owns the local clock; changing it is rejected pending a separately reviewed history policy.

`core_engine.selected_date_scheduler` validates the aware planning instant and owns date placement. The M1-C `authored_redistribution` owner enumerates complete contiguous source-unit allocations, retaining ordered source slots, repeated slots, working sets, source-scoped variants, unresolved slots and hard relationships. Its versioned lexical objective minimizes declared-primary-muscle working-set overlap on consecutive calendar dates, then working-set imbalance, squared deviation and stable source cuts. Explicit source minimum-rest constraints reject infeasible candidates. No arbitrary scientific weights or recovery claims are introduced.

New placements use the exact selected dates. Existing same-count plans, including undated legacy plans, keep their grouping/prescriptions/occurrence-to-source-slot mappings. Count changes supersede an entirely unstarted plan, retaining its source payload and replacement lineage with disjoint new occurrence identities. The API owns authenticated activation, expected revisions and user-row locking. Any execution or consent snapshot freezes the week's placement, including undone/completed work. Dated users cannot invoke server-clock count-only current regeneration, even at opposite local/server week boundaries. New local weeks use canonical generation history rather than resetting the authored source week.

Initial Auto selection uses the existing deterministic selection owner on a transient profile. Preview cannot add that profile, flush or commit planning state. `GET /plan/scheduling-context`, `POST /plan/selected-dates/preview` and selected-date `POST /plan/generate-week` carry explicit week/timezone/revision inputs. Traces include source/rule digests, declared workload, gaps, neighbor-context completeness, objective and limitations. Unknown adjacent weeks and missing muscle labels remain unknown; duration is explicitly uncalibrated.

Today selects the occurrence whose date equals the persisted timezone's local today. It resumes the same partial/completed occurrence and shows a clear rest state on dates without a workout. Week has seven accessible date checkboxes, selected count, preview followed by explicit activation, real date/session labels, warnings and focus/visibility/pre-command stale-week/revision checks. The inherited server-Sunday gate no longer blocks date placement.

## Additive migration and PostgreSQL

`0021_selected_workout_dates.py` adds six nullable fields without defaults: user timezone; plan timezone/revision; occurrence date/timezone/revision. It does not backfill ambiguous legacy rows. Downgrade requires a separately reviewed history-preserving rollback.

Rehearsal: PostgreSQL 16 Alpine, verified container `hypertrophy-m2b-qualification-20261006`, loopback port 25461, synthetic `m2b_qualification` database/user, tmpfs persistence and no production mounts. Upgraded 0020→0021 with one seeded legacy user, plan, occurrence and two logs. All six new legacy values stayed null; original columns, plan/occurrence JSON sizes, unresolved identities and RPE stayed unchanged. Original-column aggregate SHA-256 remained `2e153b54887b85c64721c2d001b6f3d6304739b860e7f970f17d6721d71ea2a0`.

Three meaningful PostgreSQL races pass: same expected revision has one winner; logging first blocks rescheduling; rescheduling first binds subsequent logging to the revised placement. Synthetic evidence and earlier configuration/collection failures are retained. The migration was **not applied live**.

## Automated qualification and baseline

All imports/tests/startup used explicit disposable SQLite/PostgreSQL targets and isolated environment variables. Python 3.12, locked API requirements, pytest-xdist 3.8.0 and web `npm ci` dependencies were used; production Next build reports 16.3.7. No inherited Compose/database defaults were used.

| Check | Observed result / limit |
|---|---|
| Core scheduling/redistribution focus | 55 passed. |
| Initial API date focus | 21 passed. |
| Review-fix API focus | 25 passed before the final identity regression was strengthened; then 5 relevant legacy-conversion/revision/count-change cases passed, including both strengthened identity cases. Final CI exercises all 26 selected-date cases. |
| PostgreSQL focused races | 3 passed; repeat after generation/Auto boundary fixes also 3 passed. No SQLite concurrency claim. |
| Web final focus / route snapshots | 23 passed in 5 files, including 4 route snapshots and local-Saturday/server-Sunday negative. |
| TypeScript / lint / production build | Passed, including a recheck after the UI review fix; lint retains one existing Today effect-dependency warning. |
| Broader core | 433 passed / 4 failed; every failure reproduced on main with identical assertions. |
| Broader web | 82 passed / 1 existing history-calendar failure; first local snapshot regeneration artifact was corrected and all 4 snapshots rechecked. Hosted CI confirms the same 82/1 result. |
| Initial hosted broader API | 608 passed / 8 failed / 16 skipped at `3560594`; all eight failure names match PR #65's main baseline. Final review-fix CI remains a separate exact-head check on PR #76. |
| Documentation comparison | 28 existing link failures / zero new; comparator exit 0. |

The four core baseline failures cover set-count normalization/state merging and canonical muscle coverage. The eight API baseline failures cover two authored Today totals, two absent licensed workbook fixtures, two adaptive-generation expectations, saved weekly-review adjustments and substitution guidance. The web baseline is duplicate `Open Today Workout` links in `history.calendar.test.tsx`. They are not repaired or hidden by this task. The local initial broader API run was interrupted after source-review fixes to avoid mixed lazy-import revisions; no complete local result is claimed. Hosted CI provides the immutable broader API run instead.

## Playwright and authored fidelity

Controlled loopback API/web, explicitly verified disposable SQLite, two synthetic users and one synthetic performed set; no real-user history. Desktop 1440×900 and mobile 390×844 rendered interactions/screenshots were inspected.

Phase 1 Tue Oct 6 / Fri Oct 9 / Sun Oct 11 preview/activation preserved 31 ordered distinct slots and 88 working sets (29/30/29); Phase 2 preserved 31 slots and 67 sets (22/22/23). Dates remained exact with gaps 3/2. Typed prescriptions and source relationships matched the loaded compiled source. Preview's database-file SHA stayed unchanged. Today logged one synthetic set and reloaded the same Oct 6 occurrence with 1/29 sets and resume enabled. Moving entirely unstarted Phase 2 dates to Wed/Fri/Sun retained identities and made Oct 6 a rest day. Tue/Wed/Thu kept those exact dates and displayed the consecutive-date warning.

Mobile controls were 48px tall; Week/Today document width equaled the 390px viewport, without horizontal overflow. A supplemental intercepted-context week-rollover test cleared old selections and sent zero activation requests; this is a simulation, not an actual clock transition. Successful final flows had no uncaught JavaScript errors. Expected rest-day 404, initial favicon/fixture/configuration errors and one transient Phase 2 dev-proxy 500 are retained: the latter recovered after isolated API restart, direct preview in 9.884s and browser retry in 8.323s, without source changes or a timeout extension. Its initial cause remains unproven.

Independent review identified and fixed legacy prescription/week reset, identity remapping on conversion, initial Auto rejection, server-Sunday gating and the legacy local/server-week overwrite. Each meaningful regression failed before its fix. PR Codex's two P1 findings are addressed by those changes; final review and CI status are tracked directly on the PR, not inferred from this document.

Codex Security independently inspected all 27 initially changed files and the final source/test delta without finding a plausible security candidate. Managed scan `141fe81d-13a0-4978-9fa1-e657023d721c` could not retain its model or canonical draft because existing global storage ancestors are group-writable without sticky protection. No global permissions were changed; there is no sealed report/SARIF or completed managed security qualification. CodeQL and GitGuardian pass on the initial PR revision.

## Evidence retention and remaining work

Sanitized summaries are committed here. Raw command output, source hashes, migration integrity JSON, baseline CI logs, browser report and 13 screenshots are retained privately under `/home/rocco/hypertrophyapp-qualification/m2b-20261006/{core,api,postgres,browser,baseline,m1c}`; they are host artifacts, not portable/public downloads. Licensed workbooks, private production records and canonical security exports are not published. Compiled-source runtime parity does not establish a fresh licensed-workbook audit; missing fixtures remain failures.

Remaining M2B work: separately approved timezone changes, missed-workout carryover/partial continuation, recurring/future-week selection, duration calibration/timer qualification, fuller known adjacent-week context and managed-security storage recovery. External calendars/reminders, load intelligence and broad Customized redesign are excluded. Existing program-switch/reset behavior is not redesigned by this slice.

Production database was not reset, reseeded or wiped; no real history was deleted. M2B is unmerged/unreleased and migration 0021 is isolated-only. Owner review and later deployment authorization remain separate.
