# CI follow-up and unchanged-base failures

The first [PR #110 CI run](https://github.com/Shadowgar/hypertrophyapp/actions/runs/39879138922) was against `52292a3`. It did not qualify the complete branch. Local focused checks are reported separately from global CI.

## Core engine: four failures reproduced on the unchanged base

CI reported **770 passed, 4 failed**. All four failed identically in an isolated checkout of merged base `fc3bd0c7b93c9d3232e6aec758e16efcca6ac583` using Python 3.12.3:

| Test | Observed mismatch on both revisions |
|---|---|
| `test_build_workout_today_payload_normalizes_sets_to_working_sets_minimum` | Expected 3 sets; received 2. |
| `test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance` | Expected bench count 2; received 1. Row count remains 2. |
| `test_resolve_scheduler_muscle_coverage_runtime_uses_canonical_contract` | Current list includes `core`; expected list omits it. |
| `test_resolve_scheduler_muscle_coverage_runtime_falls_back_to_canonical_contract_when_missing` | Current list includes `core` before `calves`; expected list omits it. |

These are verified baseline failures, not passing checks or owner-accepted deviations. This PR does not alter those decision/runtime implementations or relax their tests. Its core change adds receipt identity, set kind, actual RIR and amendment metadata to History projection. Engine behavior remains within the user's preservation boundary.

Baseline reproduction selected the exact four tests from `test_decision_workout_session.py`, `test_intelligence.py` and `test_rules_runtime.py`, with `PYTHONPATH` pointed at the base checkout, an empty inherited environment, an explicit disposable SQLite target and no production access. Result: four failures in 0.83 s. This is not a claim that the whole baseline suite was rerun.

## Changes prompted by CI

The initial web run passed 235 tests and failed one loading-state snapshot. It was capturing whichever asynchronous state won the race between initial loading and the intentionally incomplete mock response. The test now holds the initial scheduling-context/workout/soreness reads pending and asserts the loading state explicitly. This changes the test harness, not application loading behavior.

CodeQL flagged clear-text persistence of source-derived technique instructions. The saved panel now contains only workout/exercise occurrence references, parent set index, technique kind and the entry unit. On reload, source instructions, name and Authored/bodyweight flags come from the matching current API exercise. The real pending child command remains immutable. Both Authored and generic technique retry/reload regressions pass. Actual pending-entry drafts still persist locally for the requested recovery workflow; this is data minimization, not an encryption claim.

The follow-up locally passes **237 web tests across 43 files**, the production build/TypeScript check, and ESLint with zero errors and eight warnings. The final loading-mock refinement also passes all four visual-route tests.

## API: five failures reproduced on the unchanged base

The initial API CI result was **872 passed, 118 skipped, 5 failed**. Selecting the exact five cases on unchanged `fc3bd0c`, with explicit base API/core import paths and a verified disposable SQLite file, reproduces all five failures in 47.37 s:

| Test | Observed mismatch on both revisions |
|---|---|
| `test_today_total_sets_matches_progress_planned_total` / Phase 1 | Expected 30 sets; received 29. |
| `test_today_total_sets_matches_progress_planned_total` / Phase 2 | Expected 23 sets; received 22. |
| `test_generate_week_uses_saved_weekly_review_adjustments` | Expected `adaptive_review` on an Authored response; field absent. |
| `test_phase1_full_body_source_paths_point_to_real_companion_workbook` | Licensed source workbook is absent from the checkout. |
| `test_phase1_full_body_onboarding_matches_companion_workbook_table_exactly` | Same missing source workbook raises `FileNotFoundError`. |

No source workbook was copied, fabricated or committed, no Authored prescription was changed, and no test was skipped or weakened to turn these checks green. The 29-set browser completion follows the actual server-owned prescription. The source-fidelity tests remain failing qualification requirements; identifying them as baseline failures is not release acceptance.

The 135 focused local API/core checks passed as documented in [README](README.md). [Structured baseline proof](baseline-ci-proof.json) records revisions, counts and raw-log hashes; logs remain private because API output may include synthetic account data. Consult [PR #110 checks](https://github.com/Shadowgar/hypertrophyapp/pull/110/checks) for exact-head CI status. Global CI is not green, and no pending job is represented as passed.
