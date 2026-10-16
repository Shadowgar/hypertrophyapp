# M4-C1 isolated original planning core

Date: 2026-10-16. Authorization: [Issue #85](https://github.com/Shadowgar/hypertrophyapp/issues/85) and direct owner instruction to implement C1 immediately, use isolated fixtures and open a draft PR. Implementation is **an unwired draft core**, not an accepted science policy, complete M4 release or production-ready generator. No merge/deployment/migration authorization.

Base: current `main`, `27231cfe98631de7eaebf21e13b60c6d145aeeba`; remote main rechecked unchanged before publication. Branch: `m4/customized-adaptive-pilot-c1`; worktree `/tmp/hypertrophy-m4-c1`. Core/test revisions: `dfe0b78` then `b5d9468`; subsequent handoff documentation does not alter runtime code. [Bounded plan and execution ledger](../plans/m4-c1-original-planner.md).

## Exact implementation and decision ownership

| File | Implemented responsibility |
|---|---|
| [customized/__init__.py](../../packages/core-engine/core_engine/customized/__init__.py) | Isolated package, deliberately unexported by the production core façade. |
| [customized/models.py](../../packages/core-engine/core_engine/customized/models.py) | Immutable typed/versioned normalized profile, explicit clock/week context, independent catalog, numerical policy, load/variant identity, completed receipts/revisions, optional strength reports and draft outputs. |
| [customized/audit.py](../../packages/core-engine/core_engine/customized/audit.py) | Canonical content hashing, invalid-number encoding and content-bound policy-approval check. |
| [customized/planner.py](../../packages/core-engine/core_engine/customized/planner.py) | `plan_full_body`: consent/policy gates; equipment, restriction and skill filtering; preference/stability selection with stable identity tie-break; original knee/hip/push/pull action construction and three repeatable emphases; exposure/time ledgers; exact dates and explicit feasibility. |
| [customized/calibration.py](../../packages/core-engine/core_engine/customized/calibration.py) | `calibrate_working_load`: effective logical-set revision fold, completed-exposure qualification, exact comparison cohort, performed-load/effort/quality assessment, finite-inventory attainability, history-first calibration and optional self-report information. |
| [test_customized_planner.py](../../packages/core-engine/tests/test_customized_planner.py) | Synthetic planner acceptance/negative cases, including the runtime I/O-denial probe. |
| [test_customized_calibration.py](../../packages/core-engine/tests/test_customized_calibration.py) | Synthetic calibration, corrections/voids/retries, unit/basis/variant/quality and policy-gate cases. |
| [m4-c1-original-planner.md](../plans/m4-c1-original-planner.md) | Authorized scope, interface/verification plan and execution record. |
| This evidence record | Measured results, provenance, limitations and C2 decisions. |

No existing production file was modified. The new files have **zero path overlap** with the 29 changed files on open M2B PR #83 (`3f4927b`), verified through GitHub. In particular, `selected_date_scheduler.py`, `intelligence.py`, API routers/schemas/date-plan adapters and web code are unchanged. Existing plan/authority registries were left untouched to avoid conflicting with that PR; this package is linked directly from Issue #85's draft handoff.

## What works in isolation

Call `core_engine.customized.planner.plan_full_body` with a `CustomizedProfile`, `ExerciseCatalog`, `SciencePolicy | None`, `PlanningContext` and optional typed exposures/reports. Raw onboarding dictionaries are rejected at the public boundary. The test factories are explicitly synthetic examples of the full input contract; they are not imported by application code or shipped as a default policy/catalog.

The profile consumes explicit Customized consent, goal/recent-training category, three distinct selected dates within an explicit Monday–Sunday local week, valid IANA timezone, hard/flexible cap, confirmed equipment, mapped restriction tags, excluded/preferred variants, maximum confirmed skill and preferred stability. Origins are provenance-only; unsupported controls and unmapped restrictions explicitly abstain. Past-date/carryover behavior is unsupported rather than silently moving a date.

The original candidate uses four action groups: knee extension, hip extension, push and pull. Its three emphases are knee, hip and push; each repeats the exact selected equipped variants with injected anchor/emphasis doses. It does not reconstruct any authored week, source slot, source session role or paid routine. This is an inspectable candidate qualitative structure, **not a claim of complete muscle coverage or optimality**. Missing required action coverage returns infeasibility without dropping the group. Additional action families require a separately reviewed scope/policy change.

Primary/direct, secondary and unknown region counts remain separate planned-ledger entries, each tied to session and variant. No fractional coefficient, biological effective-set total or growth score is calculated. Catalog qualification is disclosed; a descriptive action tag is not expert validation.

Time output separately retains warmup, working-set duration, between-set rest, initial exercise setup, between-exercise transition and margin ranges. Catalog working-set duration must include actual set preparation/execution; transition must include any recovery/equipment movement/wait not already counted. This accounting convention is inspectable and awaits real-world timing qualification. Hard caps compare the plausible **upper bound**. A synthetic 8 + 12 + 20 + 8 + 4 = **52-minute** draft fails a **hard 45-minute** cap and retains its complete dose; flexible caps disclose the overrun. Selected dates are never invented, shifted or skipped. Neighbor spacing uses injected policy and supplied dates; missing adjacent context remains unknown.

Each exercise receives an independent calibration decision. The cohort includes exact variant, implement, equipment/calibration identity, ROM, setup/grip, unit, load basis, rep target and effort scale/target. Pounds are retained as pounds, not silently compared with kilograms; per-hand, total and machine-stack identities differ. Assistance/bodyweight/unknown load semantics abstain as unsupported in C1.

Qualified finalized exposures require exact required effective work-set coverage, actual performed load/reps/effort, acceptable reported technique and explicitly absent pain. Targets and planned prefill are never substituted for actual values. Identical retries collapse; conflicting receipt/revision/occurrence identities abstain; newest logical revisions and void tombstones control effective evidence. Partial, warmup and technique-child receipts do not supply completed work. Newer uncertain evidence cannot restore an older good working load, and pain/poor technique cannot be bypassed by a self-report. Date-only ties between distinct newest exposures abstain rather than inventing their order.

`known_working_load` retains a qualified actual attainable baseline. Sufficient high-repetition/easy-effort evidence can return `requires_calibration` with `possibly_underchallenging`, a known observed baseline, and the next value in the supplied finite inventory as **information**, not a prescribed increase. Sparse or unsuitable evidence returns `insufficient_history`; no history returns coached calibration. Optional credible, recent, exactly matching 1RM/e1RM reports expose information and method/provenance only: no percentage conversion, inferred max, mandatory max/failure test or invented starting weight. Full physical plate enumeration and inventory qualification are not implemented; callers must supply genuinely attainable values.

This reuses M2A's exact-cohort, required-completion, unknown-effort and attainable-load concepts. Existing `load_intelligence.py` deliberately remains unchanged: its public decisions require authored source slots and named authored percentages, which cannot be relabeled as Customized authority.

Every result remains `prescriptive=False`; every plan has `can_activate=False`. Absent/disabled policy returns `policy_not_approved`. Provisional or incorrectly bound approval returns no candidate unless `allow_provisional_preview=True` explicitly requests a non-prescriptive simulation. Even a synthetically approved content-bound policy yields only a draft. The core verifies hash binding, **not reviewer authenticity**; a future trusted approval registry remains required. No approved numerical policy is included in this PR. Standalone calibration also exposes `policy_status` explicitly.

Trace includes schema/owner version, qualitative rule hash, complete input hash, profile/catalog/policy/context/evidence hashes and catalog/policy source references. Session identity binds dates/timezone, selected variants, prescription and policy content; evidence-only changes alter decision traces without inventing a different planned session. The IANA timezone database is a read-only environment dependency, not a source-program input.

## Verification results

All application tests used Python 3.12.3, cleared inherited configuration (`env -i`), explicit disposable SQLite URLs, bytecode writes disabled and the isolated worktree. API imports occurred only after creating and probing a new `/tmp/hypertrophy-m4-c1-api-*/synthetic.sqlite3`; `PRAGMA database_list` verified the exact target. Both ordinary and test URLs were set identically, `.env` files were absent, knowledge/program directories pointed into the isolated checkout and logs went only to that disposable root. No live database, logs, secrets or personal records were read to construct fixtures.

| Check | Observed result |
|---|---|
| Focused new C1 tests | **71 passed** in 1.29 s. |
| Existing pure Authored/M2A baseline before implementation | **202 passed** in 6.44 s across load intelligence, authored warmups, prescription, constraints and redistribution. |
| Relevant core CI suite on final core/test code | **671 passed, 4 unchanged baseline failures**, 9.06 s; all four reproduced independently on unchanged main. |
| Scoped API regression | **82 passed, 7 deselected**, 127.29 s. Authored load, constraint authority, typed execution and correction/undo; 104 existing `datetime.utcnow()` deprecation warnings. PostgreSQL-only cases deliberately excluded. |
| Runtime boundary probe | Pass: decisions run with source/history file reads, writes, network, subprocess and database access denied; only read-only `/usr/share/zoneinfo/` access allowed. Inputs remain unchanged. |
| Documentation comparison | Pass: **0 new link failures**, 28 existing active link failures retained. Isolated documentation venv (Python 3.13.14); initial missing `referencing` dependency resolved there, no production package change. |
| Fresh review | Read-only independent static review of core/tests and final delta: no substantive findings. Reviewer did not independently run tests or validate science. |
| Protected scope | Git diff reports no changes under `programs/`, `knowledge/`, `docs/rules/` or `apps/`. Main checkout retains its preexisting log/untracked runtime artifacts. |

Reproduction: from the isolated checkout, set `PYTHONPATH=packages/core-engine`, `PYTHONDONTWRITEBYTECODE=1`, and both `DATABASE_URL` / `TEST_DATABASE_URL` to the same explicit disposable SQLite URL in a cleared environment; run `python3 -m pytest -q packages/core-engine/tests/test_customized_planner.py packages/core-engine/tests/test_customized_calibration.py`. Core CI uses `python3 -m pytest -q packages/core-engine/tests`.

For the API regression, create a new temporary root and verify the exact SQLite path using `PRAGMA database_list` **before** importing app/tests. Set `CI_TEST_ROOT`, `HIST_TEST_ROOT`, `M2A_LOAD_TEST_ROOT` to that root; point `LOG_FILE_PATH` inside it and `PROGRAMS_DIR` / `COMPILED_KNOWLEDGE_DIR` to this disposable checkout; use a synthetic JWT key. From `apps/api`, run `python3 -m pytest -q tests/test_authored_load_intelligence.py tests/test_authored_constraint_authority.py tests/test_workout_history_corrections.py tests/test_authored_typed_execution.py -k 'not postgres'`. Never inherit production defaults.

The following four core failures were independently reproduced on unchanged base `27231cf` (4 failed in 0.78 s), and are **not repaired or concealed** in C1:

- `test_decision_workout_session.py::test_build_workout_today_payload_normalizes_sets_to_working_sets_minimum`
- `test_intelligence.py::test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance`
- `test_rules_runtime.py::test_resolve_scheduler_muscle_coverage_runtime_uses_canonical_contract`
- `test_rules_runtime.py::test_resolve_scheduler_muscle_coverage_runtime_falls_back_to_canonical_contract_when_missing`

These are confirmed unchanged baseline failures; their broader contract disposition is outside C1. The core suite is not claimed green. No whole API/web suite, browser, production build, PostgreSQL concurrency/migration or training-outcome study was run for this unwired core. No schema, UI, externally reachable/auth/security boundary or dependency change requires those qualifications here. C3 must qualify its actual API/UI/persistence/date integration separately.

During test-first development, the expected missing planner/calibration modules failed collection before implementation. Subsequent failing cases identified and fixed unrelated-history status, unmapped restrictions, non-boolean finalization and explicit standalone provisional-policy labeling. The initial overly strict I/O probe also rejected the necessary IANA timezone read; the corrected probe permits only that read-only dependency. These failures were not treated as passing evidence.

## Research and rights provenance

Used the completed M4-R packet on PR #84 at **`9f7a30d9f1f7379e968b27ff3bfece31cf294437`**, without repeating PDF/Excel audits or copying their tables. Only the required original research documents were read; numerical claims were not promoted to policy, and no further paper appraisal was needed to build this software boundary.

| Research artifact under `docs/research/m4r/` on that revision | SHA-256 |
|---|---|
| `README.md` | `fe94f97e386c86786a4732fb061f8e8e10618e3e788011f6f206de7e78a573d1` |
| `batch-04-customized-program-design-standard.md` | `15e72518bd75b86737e3ba44f8578692644fe44e1cf51a5c36f51b2874031bb1` |
| `batch-05-original-exposure-and-feasibility-standard.md` | `3c8105c6a6bb34eb5edb43544faeccd353853fd28cc37edf0a653cae227ad8ad` |
| `batch-06-effort-progression-standard.md` | `42beabd80d8927eb3179183f7edb76e127f45f1d5f64f3d3666a935e5d1b7594` |
| `batch-07-science-standard-review-queue.md` | `a0cccf379f12ce874290120455e695812a97c2badb61a20656eb224359b1da71` |
| `batch-07-original-program-blueprints.md` | `272e50c1f6ea04bbc7dbf527a532565bcbbe24776d944a2953f01834b598ee76` |

[Research packet at the inspected revision](https://github.com/Shadowgar/hypertrophyapp/tree/9f7a30d9f1f7379e968b27ff3bfece31cf294437/docs/research/m4r). The structural blueprint and all tests in C1 are original engineering fixtures. No paid file bytes, private archive identifiers, workbook tables, source-program week roles or personal training records were added.

## Blockers and specific C2 decisions

C1 has no production activation path. Software tests establish deterministic software behavior, not safety, optimal dose, superior training outcomes or measured muscle growth. Before C2 can produce a real expert-reviewable numeric program, the owner and qualified reviewer need to decide:

1. **Population and goal applicability:** starting healthy-adult population, current/returning training categories, inclusion/exclusion conditions and separate hypertrophy/strength/mixed applicability. C1's fixture policy supports one synthetic goal/status pair only.
2. **Original ontology and complete coverage:** qualify actual variant/ROM/setup/implement identities, primary/secondary/unknown regions and skill/restriction mappings. Accept/revise the four core action groups and three emphases; explicitly decide knee-flexion, vertical action, shoulder, calf, arm and trunk coverage and any tradeoffs. No universal half-set accounting or metadata-v2 scoring activation.
3. **Versioned numeric prescription:** per-action/per-experience anchor and emphasis sets, rep/effort ranges and actual effort scales, rest/warmup/transition/margin ranges and spacing. Approve or replace the complete original three-day numeric candidate; every number currently exists only in synthetic fixtures. Bind accepted policy content to named scientific reviewer/owner decisions and its evidence/exception list.
4. **Calibration evidence rules:** acceptable set/exposure sufficiency and recency, effort reliability, technique/pain abstention, credibility/methods for optional 1RM/e1RM, underchallenge thresholds and bounded next observations. Decide whether any future self-report-to-working-load conversion is appropriate; C1 intentionally implements none. Keep future automatic adjustments and response experiments in C4.
5. **Physical feasibility and review outcome:** qualify real inventories and load bases/stack identities, timing measurements/uncertainty, hard-cap rejection/tradeoff language, and expected failure/abstention scenarios. Accept/revise/reject the complete candidate with named reviewer/date and remaining limitations; passing software tests cannot provide this approval.

C3 remains separate: explicit API/UI opt-in and preview consent, trusted policy/catalog admission, integration after PR #83, safe persistence/revisions and actual-date routing/browser qualification. No C2/C3/C4 implementation or production changes are included here.
