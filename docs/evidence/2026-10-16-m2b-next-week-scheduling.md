# M2B-2 next-week scheduling qualification

Owner task: 2026-10-15, resumed 2026-10-16. Base: `27231cfe98631de7eaebf21e13b60c6d145aeeba`. Implementation: `80456af9b18dba8b7a763c985879eb454e3eb2f2`, followed by Auto-preference retention, profile-input dependency binding and qualification tests on `m2b/next-week-scheduling`. This is a review candidate, not merge, deployment or milestone acceptance.

## Behavior and authority

Week selects the current or next Monday–Sunday range in the configured IANA timezone, with independent dates, saved plans, placement revisions and preview state. Preview never reserves a program week or persists a plan. Explicit activation rechecks the content digest, source predecessor, adjacent schedules and the persisted evidence inputs consumed by the generation owner under the existing user lock.

`app.selected_date_plans.resolve_source_successor` validates a unique saved predecessor, source/artifact lineage and available successor ordinal. The existing authored adapter and scheduler build that actual source week; they do not copy and relabel current prescriptions. Re-placement retains saved source content and occurrence identities for the same date count. Execution/consent snapshots still freeze started work. Current-week activity cannot silently revise an activated future plan. Auto retains the sole predecessor program without changing the saved preference.

Today uses the actual current local date. A previously activated next week becomes the current plan on local Monday without regeneration. Source artifacts, authored prescriptions, substitution consent, load and warm-up owners are unchanged. No migration was added.

PR Codex review found two correctness gaps, both reproduced before fixes: a direct future activation could omit its preview digest, and profile-backed consumers retained the old day count after a differently sized future plan became current. Future activation now requires the digest. The named `current_scheduled_days` reader derives the active current plan's count in its IANA timezone for profile/training-state/recommendation and adaptation-preview consumers, without updating stored preferences or plans. The rollover regression also checks the UTC-Monday/local-Sunday boundary.

## Disposable qualification

All local application imports, tests, migrations and startup used cleared environments and explicit disposable URLs. PostgreSQL identity was verified before application imports: task-labelled `hypertrophy-m2b2-qualification-20261015`, tmpfs-only data, no mounts, loopback `127.0.0.1:25463`, database `m2b2_qualification`, role `m2b2_test`. Existing migrations were applied only there, through `0022_authored_load_states`. No live database/configuration/service/deployment operation occurred.

The interruption removed the initial `/tmp` worktree and artifacts. Commit `80456af` survived; the worktree and disposable qualification were recreated, and the following results were retained again. Initial failed reproductions remain in the conversation, not recoverable local files.

| Check | Observed result |
|---|---|
| Focused scheduling API before final guard fixes | 98 passed: both authored phases, every 2–5 date count, correct source lineage, no-write preview, revisions, program conflicts, source exhaustion/inconsistency, frozen history, stale predecessor/history, independent weeks, rollover and cross-week digest rejection. |
| Auto retention and transition focus | 29 passed after the Auto fix. Its regression first failed with an adjacent-program conflict. |
| Final generation-dependency guards | 3 passed on the final runtime: changed profile input, Auto successor retention and changed history evidence. The profile regression first proved the old input hash unchanged; the fix binds the actual profile inputs as well as persisted evidence. |
| PR correctness fixes | 3 passed after the digest/rollover fixes: missing future digest rejected without persistence, local-Monday count reflected in profile/adaptation/coach reads without preference/plan mutation, and frozen future work still reaches the snapshot guard. All three stale-count/digest reproductions failed before their corresponding fixes. |
| PostgreSQL | 4 passed, repeated after the PR runtime fixes: one winner for concurrent current and future revisions; both logging/reschedule lock orders; current plan, frozen prescription, performed timestamps and load receipts retained unchanged. The future case passed once more with complete persisted log/command/load-state row comparisons. |
| Broader core | 604 passed / the same 4 known failures. |
| Broader web | 175 passed / the same 1 known history-calendar duplicate-link failure; all 14 selected-date UI cases passed. |
| Web build and focused lint | Production build passed, including TypeScript; focused changed-file lint passed. |
| Documentation | 295 Markdown files checked; 28 existing active-link baseline failures, zero new failures. |
| Hosted API/CI and Codex review | First candidate `96b15f7`: API 798 passed / 25 skipped / exactly the 8 known failures; core 604 passed / exactly 4 known failures; web 175 passed / exactly 1 known failure. Full web lint/typecheck/build, documentation, workflow checks, CodeQL and GitGuardian passed. Codex's two P2 findings were reproduced and fixed. Final-head results and thread status are tracked on [PR #83](https://github.com/Shadowgar/hypertrophyapp/pull/83), not inferred from local subsets. |

The broader core failures retain their identities: `test_build_workout_today_payload_normalizes_sets_to_working_sets_minimum`, `test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance`, and the two canonical/fallback `resolve_scheduler_muscle_coverage_runtime` cases. Web retains `history calendar shows planned detail on missed day with zero logged sets`. Neither baseline is repaired or hidden here. The first broader web attempt used too many host workers, produced startup/time-out errors and an expected Week snapshot mismatch; the bounded-worker recheck above supersedes that incomplete qualification. Hosted API's eight known failures require identity comparison on the PR.

## Authenticated Playwright

Chromium, desktop 1440×900 with synthetic Phase 1 and mobile viewport 390×844 with a separate synthetic Phase 2 account. In `America/New_York`, current week was October 12–18 and next week October 19–25. Both journeys selected three dates, previewed, activated, revisited both saved weeks and verified distinct occurrence IDs. Next-week dates were October 19, 22 and 24; the rendered authored ordinal advanced from 1 to 2 in each separate program. Preview left the corresponding saved plan absent.

Today returned October 16 and a current-week occurrence, never a next-week occurrence. Week and Today had no horizontal overflow; screenshots were inspected. The authenticated mobile journey recorded no page or console errors. A pre-login missing `favicon.ico` request produced one unrelated 404. One initial mobile activation was correctly blocked when the asynchronously loaded profile changed the inputs; re-previewing after profile load completed the journey without a write from the stale attempt.

Raw synthetic logs, screenshots and test outputs are local disposable artifacts under `/tmp/hypertrophy-m2b2-qualification`; they are not portable downloads and may be removed by host cleanup. No proprietary workbook, real user record or credential is published in this evidence.

## Review and limits

Independent correctness review found and verified fixes for future activation hiding a legacy current plan and a stale context response clearing a newer week's preview. The Auto fallback, profile-input hash and PR correctness fixes received separate static reviews with no remaining concrete correctness/security finding. The profile count reader performs user-scoped reads; preference writes and legacy generation remain with their existing owners.

Codex Security static review covered all five changed runtime files, the original 12-file diff, and the later Auto fallback, with no confirmed new vulnerability. Formal scan `3c205d3d-aa08-4b8e-9bff-02eeefd69349` remains running/unsealed: canonical draft storage rejected `Scan output parent must not be group- or world-writable without the sticky bit.` No global permissions/configuration were changed and no sealed report or SARIF is claimed.

New next-week generation is qualified for the two Authored Full Body bindings. A missing/ambiguous/legacy predecessor, inconsistent source lineage, exhausted source sequence, calendar gap or unqualified program progression requires reconciliation. Current legacy work must be reconciled into explicit dates before future activation can enable dated routing. Adjacent schedules inform spacing when available; missing context and uncalibrated duration remain disclosed uncertainties, not recovery/safety claims. No recurring schedule, missed-workout carryover, load-policy change, merge or deployment is included.
