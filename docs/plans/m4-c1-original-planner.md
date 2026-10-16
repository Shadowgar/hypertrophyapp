# M4-C1 original Customized core implementation plan

Status: owner-authorized isolated implementation by [Issue #85](https://github.com/Shadowgar/hypertrophyapp/issues/85), 2026-10-16. No production activation, migration, merge or numeric science-policy approval.

**Goal:** An original deterministic three-day Full Body draft and exercise-specific calibration interface, operating exclusively on explicit synthetic inputs.

**Architecture:** New `core_engine.customized` package; immutable standard-library dataclasses for normalized inputs and outputs. Separate planner, evidence/calibration, and canonical trace owners. No API, database, authored constructor, source-program loader, metadata-v2 scorer or live configuration dependency. Existing M2A functions require source identities/rule IDs; reuse their exact-cohort/effective-completion/actual-effort/attainability concepts without claiming authored rule authority.

**Spec:** Issue #85 and the owner instruction; controlling Customized/profile/load/date/metadata contracts. Research PR #84 at `9f7a30d9f1f7379e968b27ff3bfece31cf294437`, README and B04/B05/B06 standards, B07 review queue/blueprints. Research numeric values are not runtime defaults.

**Global constraints:** Explicit consent; typed normalized profile; three selected local dates retained; no proprietary topology; no runtime LLM; frozen scoring untouched; all C1 outputs are drafts and cannot activate. Inject policy by content/version/provenance. Absent/disabled policy abstains; provisional policy supports only explicitly labeled simulation. No default loads, fabricated actual effort or max test.

## Review focus

- Effective corrections and void tombstones must supersede earlier evidence; duplicate identities cannot inflate completeness.
- Pain/poor technique and newer uncertain evidence must not be bypassed with an older good exposure or self-report.
- ROM/implement/equipment calibration/unit/load-basis changes must prevent inherited load.
- A plausible upper duration over a hard cap must fail even if its lower bound fits.
- Policy approval/version changes and unsupported profile controls must never imply activation or supported behavior.

## Task 1: Typed deterministic planning core

Files: `packages/core-engine/core_engine/customized/{__init__,models,audit,planner}.py`; `packages/core-engine/tests/test_customized_planner.py`.

Consumes `CustomizedProfile`, `ExerciseCatalog`, `SciencePolicy | None`, `PlanningContext`; produces `plan_full_body(...) -> PlanPreview`.

- [x] Write and observe failing tests for consent/policy gates, exact dates/DST/week boundaries, equipment/restriction/skill/preference sensitivity, original repeatable emphasis, unweighted exposure accounting, complete time components and 52 > 45 hard cap.
- [x] Implement immutable versioned inputs, stable selection after hard filtering, explicit policy applicability, four complementary action groups with original rotating emphasis, no silent truncation, and content hashes/reasons.
- [x] Run focused tests to green; preserve failed run evidence.

## Task 2: Evidence and calibration interface

Files: `packages/core-engine/core_engine/customized/calibration.py`; `packages/core-engine/tests/test_customized_calibration.py`.

Consumes typed variant/load identity, finite attainable inventory, effective exposure revisions and optional dated credible strength reports; produces `calibrate_working_load(...) -> CalibrationDecision`. Planner attaches this interface to each exercise without persisting records.

- [x] Write and observe failing tests for actual vs planned load, exact required effective work coverage, retries/conflicts/corrections/voids/partials, variant/ROM/unit/basis/stack/assistance boundaries, recency and missing actual effort.
- [x] Implement history-first qualification, explicit self-report information then calibration, conservative underchallenge signal using injected thresholds only, quality/pain abstention, no inferred 1RM or failure prescription, inventory-bound attainability.
- [x] Run planner + calibration cases to green.

## Task 3: Regression qualification and draft handoff

- [x] Run focused M2A load/warm-up/Authored prescription/constraint/redistribution and applicable effective-history API regressions in an environment cleared of inherited settings, with verified `/tmp` SQLite targets.
- [x] Run relevant core CI, documentation checks and diff checks; preserve baseline failures by identity. No unrelated web/build/browser qualification for this unwired core.
- [x] Review complete branch; record files/results/provenance and precise C2 decisions in evidence. Prepare publication of only this branch as one draft PR, following the explicit owner request.

## Execution ledger

Ruling: Proceed inline under the owner's explicit instruction to begin implementation immediately; no new design/plan approval pause. Use focused verification as requested, not unrelated whole-application retries. Isolate work in `/tmp/hypertrophy-m4-c1` because main has unrelated runtime artifacts.

Task 1: complete; typed planner and negative boundaries implemented. Task 2: complete; effective evidence and exercise-specific calibration attached. Task 3: qualification/review and draft handoff prepared; publication/review tracked on GitHub. No merge or deployment.

Measured results and limitations: [C1 evidence](../evidence/2026-10-16-m4-c1-original-planner.md). Independent static review of `dfe0b78` and final `b5d9468` delta found no substantive issues. The 71 C1 cases pass; core CI retains four independently reproduced baseline failures. The scoped API regression passed 82 cases, excluding seven PostgreSQL-only cases. Numerical policy, ontology and production integration remain unqualified.
