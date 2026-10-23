# Authored provisional starting-load implementation

Owner approval: PR #111 `4041a558ec3160806f36eddb7f0fc90c346681a9`, specifically
approving the numerical amendment and bounded implementation. Base PR #110 stays
at `b3844398b50a64311f99ccf74411801bbd88225c`. No merge, deployment, production
migration or live-data operation is included. The [earlier characterization](README.md)
remains evidence of the pre-implementation revision, not current behavior.

## Runtime and data boundary

`core_engine.load_intelligence.decide_initial_working_load` owns the distinct
initial branch. It uses the approved inverse-Epley policy and exact Decimal
conversion/floor on declared attainable equipment. There is no browser formula
or activation of fixed 70%/72% helpers. Reported and estimated maxima have
separate output fields. Initial recommendations cannot override current work,
qualified progression or unqualified effective history.

`POST /workout/{occurrence}/initial-calibration` resolves the authenticated
account's frozen occurrence and performed source variant. The existing user-row
history lock serializes append-only calibration revisions. Identical commands
append once; changed payload conflicts. A retry returns re-evaluated current
advice rather than an obsolete estimate. Actual set/correction/undo command
replay is unchanged. The new table has an account FK and no broad cascade.
Cleanup retains existing authorization, confirmation and disabled-default gates.

Calibration records preserve original unit, magnitude, method, date, setup,
confirmation and version. Same-occurrence reload restores its own latest report;
a later occurrence reuses fields but requires confirmation. A setup identity
cannot silently acquire different grip/side/ROM/settings. Existing effective
history is re-read on projections. Source identities, dose, actual effort,
intensity techniques and historical records are never rewritten. Source warm-up
suggestions pass through `core_engine.authored_warmups`, preserving its recipe
and count while explicitly identifying the provisional working input.

The runner displays server guidance, keeps actuals editable, and protects edited
drafts/frozen pending commands from refresh. Uncertain benchmark commands retain
the exact payload across reopening/reload; retries cannot reselect a setup the
user subsequently changed. Customized remains on its independent policy.

## Verification record

- New plus existing core load/warm-up tests: **249 passed**. Full core:
  **859 passed, 4 inherited failures** (listed below).
- New calibration API cases: **74**. Combined with 41 existing Authored-load
  and 3 account-cleanup cases: **118 passed** on verified disposable PostgreSQL.
- Frontend: **284 passed** across 48 files at the original timeouts, including
  15 new calibration/transport/layout tests. TypeScript and production build
  passed; lint retains eight existing hook warnings and no errors. One earlier
  full run had an existing warm-up test timeout during a concurrent build;
  that file passed unchanged, and the final entire suite passed.
- Final-head CI and actual browser journey capture are still being completed;
  pending results are not passes.
- The initial full local API attempt stopped at collection because its isolated
  wrapper omitted `HIST_TEST_ROOT`. After fixing the wrapper, a serial attempt
  was interrupted after 112 passes, 4 failures and 2 skips to move full-suite
  qualification to CI. Two failures were the known source-count mismatches;
  two expected enabled test-only cleanup but the wrapper correctly left its
  gate disabled. Both cleanup cases passed with the CI fixture flag on the
  verified disposable target. The partial run is not full API qualification.

Core inherited failures reproduced with the unchanged approved-base owner files:
`test_build_workout_today_payload_normalizes_sets_to_working_sets_minimum`
(2 versus 3), `test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance`
(bench count 1 versus 2), and both
`test_resolve_scheduler_muscle_coverage_runtime_uses_canonical_contract` /
`test_resolve_scheduler_muscle_coverage_runtime_falls_back_to_canonical_contract_when_missing`
(extra `core` muscle). These are unresolved failures, not accepted waivers.

## Database rehearsal

The target was verified as the isolated `postgres:16-alpine` container
`workoutapp-ux-qualification-1022`, loopback port 55418, no mounts and tmpfs data.
SQL database/user identity was checked before imports and DDL. No reset, truncate,
shared-data deletion or production operation was used.

The existing synthetic fixture schema had no Alembic stamp. Running the actual
additive upgrade function preserved **487 rows across 21 existing tables** with
identical row-content hashes; [delta evidence](implementation/migration-preservation.json).
This is not presented as a full-chain migration.

A separately created disposable database, `initial_load_migration_1023`, ran the
full chain to `0025_interface_preferences`, received a synthetic account,
appearance preference and actual set, then upgraded to `0026_initial_calibration`.
All existing table hashes matched and the calibration table was empty;
[full-chain preservation evidence](implementation/full-migration-preservation.json).

## Review findings and disposition

| Finding | Correction | Regression/evidence |
|---|---|---|
| Setup details changed under the same equipment identity | Reject reassignment with 422; require a distinct setup identity | `test_declared_setup_identity_cannot_silently_change_meaning` |
| Later confirmation displaced an earlier occurrence's report | Restore matching occurrence first, then offer later report for confirmation | `test_revisiting_earlier_occurrence_restores_its_exact_saved_calibration` |
| Huge list integer caused 500 | Reject overflow as input validation; no write | `test_oversized_integer_attainable_value_rejects_without_server_error_or_writes` |
| Unresolved later targets hid prior effective work | Separate history-presence binding from progression qualification | `test_later_unresolved_source_target_history_still_blocks_initial_estimate` |
| New restriction left stale initial advice in read routes | Refresh constraints before evaluating initial branch | `test_current_restrictions_remove_saved_initial_offer_from_read_envelopes` |
| Raw display text could hide already-qualified progression | Retain existing history gate as well as independent presence check | `test_existing_progression_history_cannot_be_hidden_by_raw_display_text` |
| Resolved constraint still blocked provisional warm-up | Pass refreshed exercise to the existing warm-up owner | `test_resolved_frozen_constraint_uses_current_feasibility_for_warmups` |
| Benchmark retry reselected a newer edited equipment context | Retry retains command body without reselecting its old context | Runner transport regression |
| Long initial explanation overlapped mobile controls | Compact fixed slot and progressive disclosure; final source regression passed | Mobile/desktop geometry verified; complete journey capture pending |

PR #111 had no GitHub review threads at the pre-publication check. Internal
findings above are implementation findings, not fabricated GitHub reviews.

## Limits still open

PERS-008 and Issue #103 remain partial: this is a bounded provisional pathway,
not universal starting-load support or a clinical/optimality claim. Cold Today
performance, physical iPhone keyboard/background behavior, inherited CI failure
disposition and final-revision security qualification remain tracked separately.
The [safe physical-iPhone procedure](../unified-ux-gym/correction-pass/REMAINING.md#safe-physical-iphone-procedure-pending-execution)
uses synthetic nonproduction data; Chromium viewports do not satisfy it.

The prior canonical Codex Security export remains incomplete because its managed
writer rejects group-writable shared parent directories. No supported setup change
was available, so the blocked export was not repeated and no host permissions were
changed. See the [precise limitation](../unified-ux-gym/correction-pass/SECURITY.md).
Authorization/validation/retry tests and CodeQL, when reported, are separate
bounded checks, not a completed security scan.
