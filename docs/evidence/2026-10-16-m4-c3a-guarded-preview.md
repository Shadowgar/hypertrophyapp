# M4-C3A guarded preview: implementation and verification evidence

Date: 2026-10-16. Scope authorized by [Issue #89](https://github.com/Shadowgar/hypertrophyapp/issues/89) and direct owner instruction. C3A branch `m4/guarded-customized-preview-c3a` stacks on corrected C2 `cce0d811e6025a226e120a44cb742c8dd7a47ed5`; no merge/deploy/migration/activation. The draft PR records the final published SHA/tree. Production checkout's unrelated dirty log and existing tool/backup directories are preserved. Browser tooling adds only its own synthetic artifacts to its permitted untracked output directory.

## Focused C2 correction delivered first

PR #88 now includes `shorter_gym_standard()`, two added behavior tests and review-packet corrections, published as `cce0d811...` (tree `c3286ac6689f9191a0281805ac985802c57cbd80`). Before implementation, both new tests failed on the missing factory; afterward **91 C1/C2 tests passed in 2.65 s**. Docs/diff checks passed. The original 45-set week remains; the original bands/rest/timing assumptions were not lowered to manufacture fit.

| Gym comparison | Sets A/B/C; weekly | Estimated minutes A/B/C | Hard 60 | Coverage/dose |
|---|---|---|---|---|
| Longer | 15/15/15; 45 | 43.75–69 / 44.75–70.5 / 43.75–69 | Fails | Nominal action/region/bands complete; not an optimum |
| Shorter | 11/11/11; 33 | 35.75–57.5 / 36.75–59 / 35.75–57.5 | Fits synthetic upper bound | Six dose floors fail: lateral/rear deltoids, elbow flexors, triceps, calves, trunk; explicit acceptance required |

Both fail hard 45. Shorter work may lose hypertrophy opportunity; no equal, maximal or measured time-efficiency claim. The full original workouts and losses remain in the [C2 example](../research/m4c2/example-week.md#review-correction-shorter-original-gym-comparator). Region mappings, adapted variants, RIR subjectivity, exact thresholds and review-only deload choices remain explicitly unqualified.

## C3A altered-file manifest

| File | Concrete change |
|---|---|
| [admission.py](../../packages/core-engine/core_engine/customized/admission.py) | Immutable server registry, source/qualification/inventory pins, audience/version/expiry checks and distinct science/owner HMAC endorsements. No approved entries/keys shipped; even future admission cannot activate. |
| [test_customized_admission.py](../../packages/core-engine/tests/test_customized_admission.py) | 28 positive-control/negative cases: forged/unsigned/stale/changed/wrong-source/audience/authority/metadata/inventory. Positive authorities and attestations are fake test-only data. |
| [customized_preview_models.py](../../apps/api/app/customized_preview_models.py) | Strict bounded request, server-only principal/config/bundle types, typed synthetic-vs-approved response and unconditional nonactivation. Missing restrictions distinguished from explicit none. |
| [customized_preview_service.py](../../apps/api/app/customized_preview_service.py) | Auth/consent/scope guards, existing profile normalizer + explicit C1 profile, named C2 simulation, exact context port, actual owned facts and trace. Approved audience never returns sessions. |
| [customized_preview_http.py](../../apps/api/app/customized_preview_http.py) | Unregistered OFF-by-default FastAPI factory; production guard, server auth/allowlist/context ports, bounded read-only JSON/HTML POST routes and safe errors/headers. No production main/database import. |
| [customized_preview_view.py](../../apps/api/app/customized_preview_view.py) | Escaped consumer-style full comparison, target vs observed effort, time/cap/coverage, primary/secondary/unknown ledger and exercise-specific calibration abstention. No start/activation/log controls. |
| [test_customized_preview.py](../../apps/api/tests/test_customized_preview.py) | 30 isolated request/service/renderer/I/O cases, including final review regressions. |
| [research/m4c3a](../../research/m4c3a) (`__init__.py`, `fixtures.py`, `demo.py`) | Uninstalled explicitly synthetic host/bundles and opt-in CLI that exercises the actual guarded route and renders its response; no serving/deployment or real records. |
| [design/ownership and C3B boundary](../architecture/customized-preview.md) | Exact interfaces, active vs trace-only fields, trust assumptions, API outcomes and genuine activation requirements. |
| [plan](../plans/m4-c3a-guarded-preview.md), this evidence file | Bounded execution/verification/review record. |

All C3A files are additive. No existing production route/config/schema, Authored/M2A, history/undo, source artifacts, `programs/**`, `knowledge/**`, `docs/rules/**`, dependencies or #83 scheduling files changed. No runtime LLM or real workout writes. C2 synthetic metadata and inventories remain outside the production app/default registry.

## Demonstration and actual outcomes

`research.m4c3a.demo --synthetic-review` calls the isolated app with a synthetic server-side principal/context and emits HTML from its JSON results. Without the flag, generation is rejected. This does not start production or expose a service. Example artifact `/tmp/hypertrophy-c3a-demo/preview.html` contains both full candidates, six dated sessions/42 exercise cards, no activation/logging controls, and visible six-floor short-option losses. Pinned and ambient dependency environments produced byte-identical HTML. HTML SHA-256: `ed4c4a8ad3a0204db1186967431e0219b71ebfc00cde8f71433fa02915685ff8`.

| Request/context | Observed outcome |
|---|---|
| Default factory, or production environment even with enabled flag | 404 feature disabled before auth/context/planning; no persistence |
| Enabled test app without authenticator/session | 401; no planning |
| Authenticated subject without scope/allowlist | 403; no planning |
| Synthetic shorter bundle + exact dates/skill/equipment/reported restrictions + six explicit dose tradeoffs | 200, `synthetic_review_preview`, `policy_not_approved`, `accepted_limited_candidate`, upper minutes `[57.5,59,57.5]`, `can_activate=false` |
| Same short bundle without accepted tradeoffs | 200 explained infeasible/incomplete preview; no silent dose repair |
| Longer bundle + hard60 | 200 explained infeasible preview; 45 sets retained |
| `approved_prescription`, empty trusted registry | 409 `policy_not_approved`, zero sessions; no synthetic fallback |
| Simulated future admitted decision | `activation_disabled`, zero sessions; no activation implementation |
| Missing/null restrictions vs explicit `[]` | 409 needs information vs explicit reported-none preview; neither implies medical clearance |
| Client policy/reviewer/approval/catalog/flag fields or malformed date | 422 safe error, rejected values not echoed |
| Body >16 KiB | 413 bounded rejection |
| Activation or set-log path | 404; no such route |

Every result preserves unknown observed effort and unset working load unless exactly comparable synthetic evidence exists. Owned pain, technique, stale-evidence and unsupported-load reasons remain visible in JSON and per-exercise HTML. Optional max information is not converted to a working weight.

## Focused verification and independent review

Final combined run after the review fixes and explicit-vs-missing optional-input provenance regression: **366 passed** (28 admission + 30 preview + 91 C1/C2 + 202 existing M2A/Authored + 15 existing GeneratedDecisionProfile/GeneratedTrainingProfile). Pinned-dependency run: **13.97 s**, Python 3.13.14, FastAPI 0.142.1, Starlette 1.7.0, Pydantic 2.14.1, pytest 9.0.3; one Starlette TestClient deprecation warning for the repository-pinned httpx 0.28.1. No dependency change was made. Before the final provenance-only regression, 365 cases also passed on the ambient Python 3.12.3/FastAPI 0.116.1/Starlette 0.47.3 environment (14.85 s, one harness assertion-rewrite warning). These are focused runs, not whole-repository green CI.

The final harness clears inherited environment, pins both DB URLs to the same unused `/tmp/hypertrophy-c3a-api-unit/unused.sqlite3`, checks no inherited `.env`, asserts that file remains absent before/after, and asserts neither `app.database` nor `app.main` was imported. No persistence test, schema creation, destructive reset helper, real signing key, account or live record is used. Runtime I/O-denial subprocesses passed for C1 and C3A decisions (writes, sockets, DB and subprocess blocked; IANA timezone reads allowed). Initial RED phases showed missing admission/HTTP modules; final review regressions failed before their fixes.

Reproduce in a disposable checkout, before imports, with verified local paths and no `.env`:

```sh
env -i PATH=/usr/bin:/bin PYTHONPATH=packages/core-engine:apps/api:. PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=sqlite:////tmp/hypertrophy-c3a-api-unit/unused.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/hypertrophy-c3a-api-unit/unused.sqlite3 CI_TEST_ROOT=/tmp/hypertrophy-c3a-api-unit PROGRAMS_DIR="$PWD/programs" COMPILED_KNOWLEDGE_DIR="$PWD/knowledge/compiled" LOG_FILE_PATH=/tmp/hypertrophy-c3a-api-unit/api.log python3 -m pytest -q packages/core-engine/tests/test_customized_admission.py packages/core-engine/tests/test_customized_pilot.py packages/core-engine/tests/test_customized_planner.py packages/core-engine/tests/test_customized_calibration.py packages/core-engine/tests/test_load_intelligence.py packages/core-engine/tests/test_authored_prescription.py packages/core-engine/tests/test_authored_constraints.py packages/core-engine/tests/test_authored_warmups.py packages/core-engine/tests/test_authored_redistribution.py apps/api/tests/test_customized_preview.py apps/api/tests/test_generated_decision_profile.py apps/api/tests/test_generated_training_profile.py
```

For the synthetic HTML, use the same isolated environment and `python3 -m research.m4c3a.demo --synthetic-review > /tmp/preview.html`. No official program is saved. Test-only inventory and original numerical candidates are visible review data, not real prescriptions.

Independent read-only review of `cce0d811..ce36e99` read all eight changed source files, both tests, plan and direct support. It found two P2 correctness gaps: omitted restrictions became empty, and HTML hid specific calibration abstention reasons. Both were reproduced (four failing regressions), fixed in one pass and verified by the scoped suite. A final author provenance check also reproduced a missing-origin field; it now distinguishes omitted optional controls from explicit clearing without changing sessions, with a separate RED→GREEN regression and final combined verification. No further substantive authority-bypass/signature/HTML finding was identified by that reviewer; no independent test rerun or scientific qualification was claimed.

Review boundary decisions: scientific efficacy/numbers, actual authority credentials/evidence and real inventory remain unqualified; production auth/deployment/persistence/activation remain outside C3A and must be qualified before C3B. Browser/device qualification is separately scoped below. If these assumptions were mistaken, treating this preview as live would violate the stated admission boundary; C3A therefore exposes no activation path. No minor findings were deferred.

Documentation checker against corrected C2 passed: **0 new link failures**, 28 existing baseline exceptions. External URLs were not fetched/certified. Staged diff whitespace check passed.

## Browser evidence and security-export limitation

Playwright inspected the **static synthetic artifact produced by the actual in-process adapter**, at desktop 1440×1000 and mobile 390×844 on a temporary loopback-only artifact server. Verified six sessions, 42 exercises, 45/33-set comparison, unknown observed effort, exact hard-cap/tradeoff text, no buttons/forms, no horizontal page overflow, candidate anchor navigation and expandable region accounting. Final navigation had **zero console errors/warnings**. Initial static-host favicon 404 was isolated to the disposable viewer and resolved there with an empty icon placeholder; no app source workaround. The temporary artifact server is stopped after inspection.

Screenshots are local synthetic evidence: `/tmp/hypertrophy-c3a-demo/desktop-overview.png`, `desktop.png` and `mobile.png`. The browser tool can write only its configured checkout output directory, so those newly generated files were copied into `/tmp`; pre-existing tool outputs were left alone. The final provenance-only trace addition changes the collapsed diagnostic content, not the inspected workout cards/layout; its omission/clearing behavior is covered by the final regression. This is not an authenticated production browser session, real-device/manual training test or real inventory qualification.

Codex Security diff scan `82e2e1b2-dde3-48ab-af18-be383eabae97` targeted exact immutable `cce0d811..ce36e99`. Capability preflight passed; eight changed source files were inventoried and reviewed, zero security candidates recorded. **Canonical draft export failed** with the host guard: “Scan output parent must not be group- or world-writable without the sticky bit.” No host permissions were changed or guard bypass attempted. The scan/context was preserved for authorized recovery; no sealed/completed report, SARIF, later-fix security certification or deployed-security qualification is claimed. The two correctness fixes are covered by RED→GREEN tests and final suite; the original review was not rerun as a pretend clean scan.

## Existing hosted CI, not repaired here

C2 original head `a427fb8...`, [run 38941928075](https://github.com/Shadowgar/hypertrophyapp/actions/runs/38941928075), completed red. Core: **689 passed/4 existing failures**; API: **779 passed/8 existing failures/25 skipped**, 571.53 s; web: **173 passed/1 failed**, ambiguous history-calendar “Open Today Workout” query already documented in the September baseline. Documentation, workflow checks and container build passed. API log job `117111503024` was inspected once: its exact eight names/fingerprints match C1 and the recorded base/head parity; no new API failure emerged. [C2 classification](2026-10-16-m4-c2-full-body-pilot.md#existing-red-hosted-ci-exact-revision-and-basehead-classification) remains applicable.

Corrected C2 base `cce0d811...`, [run 38943914219](https://github.com/Shadowgar/hypertrophyapp/actions/runs/38943914219), also completed red: core **691 passed/4 same failures**, API **779 passed/8 same failures/25 skipped** (425.48 s), web **173 passed/1 failed**. Those current-base job logs were read once; the same four core names and all eight API fingerprints remain, with no new API failure. Documentation, workflow checks and container build passed.

No expensive unrelated suite retry, CI repair, production workload pause or live-target test was performed. New C3A hosted checks are reported by the draft PR at its published revision; local focused passes do not supersede inherited red CI.

## Genuine C3B handoff

The only activation decisions are the [five explicit C3B gates](../architecture/customized-preview.md#only-c3b-activation-decisions): qualified professional/owner numerical approval and trusted authority provisioning; real metadata/inventory qualification and accepted workload tradeoffs; user-owned consent/revision/occurrence/migration scope; #83-compatible actual dates/two-week context; real auth/security and manual device/release qualification. No new research cycle or C4/Military development is required to review those decisions. C3A requests no live activation permission.
