# M4-C2 isolated complete Full Body candidate: verification evidence

Date: 2026-10-16. Authorization: [Issue #87](https://github.com/Shadowgar/hypertrophyapp/issues/87) and direct owner instruction. Stack base: C1 `a4b88df90f6a9c1a6cad8f7a33c29dd6954b25d2`, tree `4d55839f5a1c0d3fdbfbe275c97cb0304cdfe0cc`. C2 initial implementation commit: `52bb049`; subsequent changes add/correct the review packet only. The draft PR's published commit/tree is the final review identity. No merge, deployment, production writes or release acceptance.

## Exact change manifest and owners

| Files | Actual behavior / authority |
|---|---|
| [pilot_models.py](../../packages/core-engine/core_engine/customized/pilot_models.py) | Immutable original session/slot design, explicit region bands, omission receipts, coverage and region-summary result. |
| [pilot.py](../../packages/core-engine/core_engine/customized/pilot.py) | `plan_pilot` owns offline complete-program validation and coverage: 13 actions, 13 desired regions, three exact dates, original injected slots; calls C1 selection/time/calibration; hashes standard/design/input/evidence; explicit incompleteness, consent and hard-cap boundaries. |
| [planner.py](../../packages/core-engine/core_engine/customized/planner.py) | Only existing-file code change: optional explicit action vocabulary for `_validation`. C1 vocabulary remains default. No Authored/runtime façade changes. |
| [test_customized_pilot.py](../../packages/core-engine/tests/test_customized_pilot.py) | 18 actual C2 scenario tests with deterministic replay and negative authority boundaries. |
| [research/m4c2](../../research/m4c2) (`__init__.py`, `catalog.py`, `science.py`, `examples.py`) | Uninstalled, offline-only original descriptive inventory, explicit numerical candidates, synthetic scenarios and renderer. No runtime import/wiring or silent default. |
| [review packet](../research/m4c2/README.md) (`README.md`, `training-science-standard-v1.md`, `exercise-ontology.md`, `example-week.md`) | Complete original example, finite numerical decision matrix, evidence/population/conflicts, source/inference limits and concrete professional/owner approvals pending. |
| [implementation plan](../plans/m4-c2-full-body-pilot.md), this evidence file | Scope, sequencing, tests, baseline and handoff. |

`prescriptive=False`, `can_activate=False` and `policy_status=review_required` remain unconditional C2 outputs; even a valid or forged local policy hash cannot activate. Calibration is forced through provisional simulation without an approval token. Source/metadata consistency checks are not a trusted admission registry or human endorsement. All 20 exercise metadata records remain human-unqualified. Numerical values are explicit proposals, never accepted science defaults.

No changes to `apps/**`, migrations/database schema, `programs/**`, `knowledge/**`, `docs/rules/**`, source assets, production configs/services, existing Authored/M2A logic, scheduling PR #83 files or frozen scoring. No runtime LLM, network call, database write or source-program layout is introduced by the planner.

## Focused checks

| Check | Result and limit |
|---|---|
| New C2 behavior plus unchanged C1 cases | **89 passed**: 18 C2 + 71 C1. Failing-first development included absence of the new module, source/selection and explicit dose-omission cases, and unknown-ledger reporting before implementation/fixes. |
| Final combined focused suite | **291 passed in 8.95 s**: above 89 + 202 existing M2A load intelligence / Authored prescription, constraints, warmups and redistribution cases. |
| Code review | Independent read-only review of `a4b88df..52bb049`: no substantive findings. Final packet/code consistency review also found no substantive issues. Static review only; reviewer did not independently run tests or validate exercise sources/physiology. |
| Documentation | Offline checker against C1 base: passed with the existing 28 baseline link exceptions; external URLs are not certified by that checker. |
| Diff and protected-path check | `git diff --check` passed; only the manifest above differs from C1. |
| API baseline classification | 16 isolated single-case runs, eight on unchanged main and the same eight on C1: matching failure fingerprints, detailed below. No full API rerun in C2. |

Core tests were run in `/tmp/hypertrophy-m4-c2` with a cleared environment, explicit `PYTHONPATH`, bytecode disabled and ordinary/test DB URLs both `sqlite:////tmp/hypertrophy-m4-c2-unit.sqlite3`. These pure tests do not create/use that DB. C1's runtime I/O-denial test passed again (writes/network/process/database denied, IANA zone data read allowed). Test inputs are synthetic. No application startup, live config import, production service pause, build or deployment was needed.

Reproduce the focused suite from the isolated repository root:

```sh
env -i PATH=/usr/bin:/bin PYTHONPATH=packages/core-engine:. PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=sqlite:////tmp/hypertrophy-m4-c2-unit.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/hypertrophy-m4-c2-unit.sqlite3 python3 -m pytest -q packages/core-engine/tests/test_customized_pilot.py packages/core-engine/tests/test_customized_planner.py packages/core-engine/tests/test_customized_calibration.py packages/core-engine/tests/test_load_intelligence.py packages/core-engine/tests/test_authored_prescription.py packages/core-engine/tests/test_authored_constraints.py packages/core-engine/tests/test_authored_warmups.py packages/core-engine/tests/test_authored_redistribution.py
```

Scenarios cover full gym week and dose bands; new/returning context; missing equipment/metadata; explicit dumbbell action/dose omissions; lower skill; hard 45/60 and longer durations; source-content/action falsification; unknown ledgers; preference sensitivity; standalone completed one-set calibration; real performed 20 kg vs 99 kg prefill; easy-but-good-form, pain/technique/unknown effort; optional 1RM information only; substitution without inherited weight; unavailable higher inventory; missing/past date and DST; consent and nonactivation despite local approval. C1's exact 52 > 45-minute hard-cap regression also passes. Adjacent-week carryover/revisions and missed-session recovery routing remain C3, not claimed implemented.

## Existing red hosted CI: exact revision and base/head classification

C1 hosted [workflow run 38935857580](https://github.com/Shadowgar/hypertrophyapp/actions/runs/38935857580) at `a4b88df90f6a9c1a6cad8f7a33c29dd6954b25d2` completed red: core **671 passed / 4 failed**; API **779 passed / 8 failed / 25 skipped**. Documentation/workflow checks passed; web/container checks were skipped; aggregate failed. These counts are inherited observations, not a claim that C2 full CI passed.

Only the eight named API cases were revisited. Main baseline was `27231cfe98631de7eaebf21e13b60c6d145aeeba` in `/tmp/hypertrophy-m4-c1-baseline`; C1 head was `a4b88df...` in `/tmp/hypertrophy-m4-c1`. The relevant application/test files are unchanged between them. Each case used a **fresh unique temporary SQLite database**, ordinary/test URLs identical, exact `PRAGMA database_list` path verified before application imports, synthetic signing key/log root and checkout-owned program paths. Neither checkout contained an inherited `.env`.

Legacy test `_reset_db` was replaced in the local harness with a **create-only** function that asserts the verified engine path and an empty database, then creates tables once. `MetaData.drop_all` was replaced with an assertion failure. Test bodies/assertions were unchanged. This honors DB_SAFETY_LOCK; these are adapted-fixture local parity runs, not byte-identical hosted-environment qualification. No database was dropped/reset/reseeded and no production target was accessed. Local scripts/logs remain under `/tmp/hypertrophy-m4-c2-baseline-*` and `/tmp/hypertrophy-c2-baseline-*`.

| API case (under `apps/api/tests/`) | Main / C1 result | Classification and remaining question |
|---|---|---|
| `test_program_catalog_and_selection.py::test_adaptive_gold_generate_week_includes_core_slot_when_equipment_available` | Both fail `(12 - 10) <= 1` | Existing adaptive/generation set-balance assertion; unrelated to unimported C1/C2 core. Contract disposition not decided here. |
| Same file `test_adaptive_gold_generate_week_uses_authored_deload_week_six` | Both fail `all(...)` | Existing adaptive/authored-deload assertion. No authority to fix by changing authored or generated policy. |
| `test_authored_generated_path_regression.py::test_today_total_sets_matches_progress_planned_total[pure_bodybuilding_phase_1_full_body-30]` | Both return 29 vs expected 30 | Existing Today/planned-total discrepancy, unchanged by C1; contract/root-cause resolution remains separate. |
| Same test `[pure_bodybuilding_phase_2_full_body-23]` | Both return 22 vs expected 23 | Same existing discrepancy for Phase 2; not silently marked obsolete or repaired. |
| `test_workout_session_state.py::test_adaptive_gold_fourth_exercise_today_and_log_set_preserve_substitution_guidance` | Both `StopIteration` | Existing fixture/selected exercise expectation mismatch. No C2 substitution/load transfer change. |
| `test_weekly_review.py::test_generate_week_uses_saved_weekly_review_adjustments` | Both missing `adaptive_review` | Existing generation/review contract expectation; not a C1 regression or approved change request. |
| `test_phase1_full_body_source_fidelity.py::test_phase1_full_body_source_paths_point_to_real_companion_workbook` | Both workbook path does not exist | Environment/private source fixture gap; no private archive restored or repeated audit. |
| Same file `test_phase1_full_body_onboarding_matches_companion_workbook_table_exactly` | Both `FileNotFoundError` for companion workbook | Same private fixture gap. Actual workbook parity not qualified by these runs. |

All 16 runs failed at their expected existing assertion/fixture fingerprint. “Baseline” establishes reproduction and non-introduction; it does **not** approve the behavior, invalidate the test or close the underlying defect. Hosted log review and local base/head parity now satisfy the requested finite classification; no unrelated fixes or full expensive reruns were attempted.

The four existing core failures had already been reproduced on unchanged main in C1:

- `test_decision_workout_session.py::test_build_workout_today_payload_normalizes_sets_to_working_sets_minimum`
- `test_intelligence.py::test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance`
- `test_rules_runtime.py::test_resolve_scheduler_muscle_coverage_runtime_uses_canonical_contract`
- `test_rules_runtime.py::test_resolve_scheduler_muscle_coverage_runtime_falls_back_to_canonical_contract_when_missing`

C2 does not rerun unrelated whole API/web/PostgreSQL/browser/build suites. This package has no changed UI, API, credentials, dependency, schema or external security surface requiring those qualifications. The draft PR's checks may still be red from this baseline; report their actual state rather than asserting a green repository.

## Remaining decisions and limitations

The finite [science decision matrix](../research/m4c2/training-science-standard-v1.md) is ready for a verifiably assigned professional and owner. All exact numbers remain provisional. Real technique/anatomy qualification, individual contraindications, time-motion observations and physiological outcomes are not proven by synthetic tests. The current-user full gym example is about 44–71 minutes, failing hard 45 and hard 60; reduced dumbbell coverage requires three explicit tradeoffs. Choosing a shorter design or accepting longer sessions is a real owner/professional decision.

Trusted admission/inventory/ROM validation, actual API/UI/date revision/two-week carryover belong to C3. Longer-term progression/deload execution belongs to C4; its numerical suggestions in this packet are review-only. Military/Hybrid remains a separate goal policy. No release/activation is requested by this evidence.
