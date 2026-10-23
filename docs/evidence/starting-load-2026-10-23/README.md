# Starting-load slice: current behavior and specific policy review

Date: 2026-10-23. Application source: **PR #110
`b3844398b50a64311f99ccf74411801bbd88225c`**, verified against GitHub before this
isolated stacked branch was created. PR #110 is unchanged. This package adds
only a proposed numerical amendment, reproducible characterization and affected
traceability. **No new starting-load calculation, API/UI behavior or schema is
implemented.** The request explicitly requires review first if numerical policy
is absent; that condition applies here.

[Specific amendment and worked examples](../../contracts/proposals/authored-starting-load-v1.md)
· [Actual API observations](observations.json) · [Executable reproduction](characterize.py).

## Policy provenance and implementation gap

- Desired behavior: owner assignment, Issue #103, PERS-008 and Wave A/M2A.
  PR #109 was read directly at `4ac9c49b8c9f274dd70784f4ec9027e65592f657`:
  [personal requirements](https://github.com/Shadowgar/hypertrophyapp/blob/4ac9c49b8c9f274dd70784f4ec9027e65592f657/docs/requirements/personal-workoutapp-2026-10-21.md)
  and [crosswalk](https://github.com/Shadowgar/hypertrophyapp/blob/4ac9c49b8c9f274dd70784f4ec9027e65592f657/docs/roadmap/personal-capability-crosswalk-2026-10-21.md).
  Its older read-only handoff is not the current implementation authorization.
- Reviewed owner: `core_engine.load_intelligence`, the
  [M2A-1 design](../../plans/m2a-load-intelligence-design.md) and
  [load contract](../../contracts/load-progression.md). Existing policy interprets
  qualified completed work, actual RPE and source-relative progression. It has
  no known-1RM/recent-calibration input or initial rep-aware calculation.
- `AtlasRunner` keeps `knownMax` in component state and explicitly calls it
  reference-only. The value is not submitted, persisted or consumed by the load
  owner. “Recent performance” displays an available baseline; it does not accept
  a recent weight/reps/effort calibration report. A reference is not PERS-008
  acceptance.
- Retained `oneRepMax.ts` uses a fixed 70%; the legacy
  `rules_runtime.resolve_starting_load` can use the canonical fixed 72%. Neither
  uses the first prescribed rep target. A rule's presence is not approval to
  activate it through another owner. No supported reviewed conversion for the
  required initial estimate was found in the current load contract/design or
  their referenced M2A evidence. The proposal adds that one decision rather
  than reopening the training architecture or visual selection.

## Cross-Body trace and observed distinctions

Actual call path: approved runner → Today load-context preview →
`POST /workout/{occurrence}/load-guidance` → owner-bound occurrence/slot and
Authored permission checks → `project_authored_load_feedback` → effective
receipt/cohort summarization → `decide_next_working_load` and, for current
partial work, `decide_remaining_working_load`. The API wraps owner facts and
advice/evidence identity; the runner displays them and preserves actual drafts.
Authored source warm-ups retain their separate qualified source owner.

The reproduction loads the repository's current compiled Phase 1 first
Cross-Body slot: **3 work sets, 10–12 reps, early RPE 7–8, last RPE 8–9,
1 source warm-up**, with the existing last-set technique. It does not parse,
copy or fabricate a licensed workbook. Synthetic occurrences reuse that exact
prescription for controlled comparisons; they are not claimed as a real user's
program progression or a fresh source-fidelity certification.

| Scenario | Actual owner result | Diagnosis |
|---|---|---|
| No recorded work, exact declared machine/basis/increment | monitor, no weight; `no_completed_exposure_evidence` | Missing history; no initial-calibration branch exists |
| Two of three source work sets, explicit setup/actual RPE | next exposure monitor, `incomplete_exposure`; remaining sets hold actual 40 kg | Incomplete exposure, not three completed exposures or a new initial estimate |
| All three comparable 40 kg × 11 sets, actual RPE 7.5/7.5/8.5 | **hold 40 kg**, prefill available, 1 comparable completed exposure | Existing actionable history authority works |
| Same history, requested different cable machine | monitor, no matching exposure in that cohort | Incompatible setup, not globally missing history |
| Unknown basis / absent machine identity | monitor with explicit context reason | Missing context; do not infer from the exercise name |
| Complete work but actual RPE omitted | monitor, `actual_rpe_missing` | Missing evidence; source RPE remains a target, not actual effort |
| Correct first 40 kg set to 35 kg; replay same correction | monitor, `mixed_working_loads`; only one replacement | Effective history changes derived advice without duplicate correction |
| Undo last work set after correction | monitor, incomplete/mixed; all 4 receipt rows retained, 2 effective | Voided work stops completing an exposure; audit remains |
| Foreign account requests the occurrence | 404 | Account boundary retained |

The script also verifies canonical 40 kg through kg→lb→kg context previews,
identical repeated decisions and unchanged frozen source prescriptions on every
created occurrence. No frontend formula, inferred 1RM or completed work is
inserted. This establishes the separate failure categories in synthetic data;
**the live owner's account/history was not queried**, so its particular absent
fields are not guessed. The confirmed implementation gap is the missing
calibration admission/calculation/persistence, not evidence of a broken
completed-exposure arithmetic rule.

## Verification performed

- Existing pure load-intelligence and Authored warm-up suites: **160 passed**,
  3.99 s, Python 3.12, explicit isolated environment. No database import in those
  suites; both database URLs nevertheless point to a task-local unused SQLite
  file, never inherited defaults.
- Existing Authored API load-intelligence suite: **41 passed**, **0 skipped**,
  16 existing deprecation warnings, 40.07 s, explicitly verified disposable
  PostgreSQL. Includes ownership, context/variant/slot isolation, correction,
  undo, reconstruction, finite-input and PostgreSQL concurrency boundaries.
- `characterize.py`: **all assertions passed**, 15 reported observations. Real
  API transactions on the same verified target, unique synthetic `example.com`
  accounts, exact retries, correction/undo and source-snapshot checks. No reset,
  wipe or deletion was used to prepare or finish the run.
- An initial characterization attempt omitted the plan adapter's required
  `recommended_working_weight` presentation field and raised `KeyError` before
  logging. The harness now supplies an explicit zero/unknown compatibility
  placeholder; the owner still returns no recommendation without evidence.
  This was a harness failure, not a passing run or an application fix. The
  successful rerun used new synthetic accounts and did not erase the earlier
  data. No full first-run raw log is included in this package.

Target verification before application imports: dedicated container
`workoutapp-ux-qualification-1022`, `postgres:16-alpine`, loopback
`127.0.0.1:55418`, **no mounted volumes**, tmpfs data directory; SQL identity
`m2a_qualification` / `m2a_test`. The reproduction refuses another URL/identity.
Credentials remain private. It creates synthetic records only; it never runs
DDL/reset helpers. Reproduction requires a separately verified migrated target
and isolated environment as specified by [DB_SAFETY_LOCK](../../../DB_SAFETY_LOCK.md).

These checks qualify existing behavior at the stated application revision, not
the proposed numerical policy or its future UI. The two earlier suites are
existing regressions, not newly implemented feature tests. Final package CI and
exact head are recorded on the stacked PR, avoiding a moving-head evidence claim.

## Acceptance still open

**PERS-008 / Issue #103 remain partial.** The proposal contains an eligible
worked provisional example, an ineligible fallback example and a history-first
example. Only fallback/history behavior was demonstrated in the actual existing
application; the eligible provisional result is **not implemented or
demonstrated in the runner**. Calibration persistence/reload, new-policy unit/
increment/invalid-input tests and mobile/desktop provisional-load journeys remain
implementation/qualification work after the specific numerical decision.

Cold Today performance, physical iPhone keyboard/background acceptance,
inherited CI disposition and final-revision security qualification remain open.
The last complete PR #110 CI at `b384439` had web 269 passed; API 875 passed,
5 failed, 118 skipped; core 770 passed, 4 failed. The nine failures reproduced
on unchanged base and remain failures, not waivers. This package does not rerun
or declare the full application suite green. No licensed fixture is fabricated.
The [prior limitation and safe physical-device instructions](../unified-ux-gym/correction-pass/REMAINING.md)
remain applicable. The [blocked canonical security export](../unified-ux-gym/correction-pass/SECURITY.md)
was not repeated: no supported setup change exists to resolve it.

No application redesign, broad Home/onboarding slice, Apple/platform/API
integration, runtime LLM, unrelated engine rewrite, merge, deployment,
production migration or live-data operation is part of this package.
