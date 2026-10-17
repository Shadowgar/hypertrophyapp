# M4-C3B1 isolated account lifecycle evidence

Date: 2026-10-17. Authorization: [Issue #92](https://github.com/Shadowgar/hypertrophyapp/issues/92) and direct owner instruction, after reading the 2026-10-16 owner review on [PR #90](https://github.com/Shadowgar/hypertrophyapp/pull/90). Verified stack base: `3fe4ef381fee730ea13e0957201dd9bfe57ae9dc`. New branch `m4/account-owned-customized-lifecycle-c3b1`; the draft PR records the published head/tree. No merge/deploy/migration/live data or workout activation. [Architecture and limitations](../architecture/customized-account-lifecycle.md), [bounded plan](../plans/m4-c3b1-account-lifecycle.md).

## Actual manifest

- `apps/api/app/customized_lifecycle.py`: command owner, immutable evidence snapshots, append-only lifecycle, authentic challenge/receipt, retry/CAS, freshness and permanently blocked authorization.
- `customized_lifecycle_models.py`: strict command/actor/transaction port contracts; no client authority.
- `customized_lifecycle_schedule.py`: versioned read-only account-owned context and adjacent dates; no #83 import or date mutation.
- `customized_lifecycle_http.py`: separate disabled-by-default factory and explicit existing-current-user dependency bridge.
- `customized_lifecycle_view.py`: actual C3A rendering plus explicit candidate consent/revision/decline/withdraw and blockers; stale-response guards.
- `apps/api/app/customized_preview_service.py`: internal typed evidence-return seam; same public preview interface/training decisions.
- `apps/api/app/customized_preview_http.py`: existing bounded isolated middleware accepts server-owned response headers; C3A default unchanged.
- `apps/api/tests/test_customized_lifecycle.py`, `test_customized_lifecycle_http.py`: 40 account/storage/HTTP cases including review regressions.
- `apps/api/tests/test_customized_preview.py`: child-process explicit repository import paths/cwd; existing I/O-denial checks preserved.
- `research/m4c3b1/{__init__.py,store.py,demo.py,browser_qualification.js}`: uninstalled synthetic/disposable adapter, opt-in demo and repeatable Playwright qualification function.
- This evidence, architecture and bounded plan: explicit ownership, flow, results and release limits.

Changed contracts: GEN-001/002/003/004/006/007/009, proposal-side history/retry/revision integrity, selected-date context and account/object authorization. No production schemas/routes/dependencies, Authored/M2A prescription/load logic, correction/undo writers, #83 scheduling files or protected `programs/**`, `knowledge/**`, `docs/rules/**` changed. Git diff against the stack base verified those protected paths empty. Existing Authored source tree objects remain identical; no PDF/Excel re-audit was run.

## Synthetic flow reproduced

`python -m research.m4c3b1.demo --synthetic-review` invokes the actual guarded HTTP factory/TestClient against exclusively created disposable SQLite. Without the flag it exits. The optional `--serve --port 8766` binds loopback only, has explicitly fake research credentials and no production auth/startup imports; it is not an app deployment.

Recorded CLI sequence: `review_required` (plan1/revision2) → server challenge (revision3) → `accepted_candidate` (revision4) → `activation_blocked` (revision5) → new long candidate revision (plan2/revision7) → `declined` (revision8). The short snapshot contains 33 sets and 57.5/59/57.5-minute upper bounds; acceptance requires 20 exact acknowledgements, including all 12 removed sets and six unapproved dose gaps. Old long/short rules are preserved.

A stale decline returned **409 stale_revision**. Bob reading Alice's proposal returned **404**, identical to nonexistent ID. Replaying the original accept returned its historical accepted receipt, while the current object remained declined. Eight stored events retained original snapshot/consent and new candidate. Reopening the marked database reconstructed the same current object and prior history. `can_activate=False`; no workout table/writer/session path exists.

Hard60 long and hard45 short stay infeasible with unchanged 45/33 sets. Skill/restriction/training-context unknowns produce `requires_information`; observed RIR remains unknown. Authored started/completed/partial/planned retained context blocks consent without changing its slots/prescription/date hashes. Missing/unknown/incompatible reference comparisons block reduced-candidate consent. Policy/catalog/reference/history corrections and scheduling revision changes require a fresh preview.

## Test environment and results

Fresh `/tmp` worktree and venv; Python 3.13.14, repository-pinned FastAPI 0.142.1, Starlette 1.7.0, SQLAlchemy 2.0.36, PyJWT 2.15.1, pytest 9.0.3; resolved Pydantic 2.13.5. No dependency files changed. Every test/import/demo used `env -i`, explicit `DATABASE_URL` and `TEST_DATABASE_URL` pointing at the same **unused** `/tmp/hypertrophy-c3b1-unused.sqlite`, isolated logs/test paths, `PYTHONDONTWRITEBYTECODE=1`, no checkout `.env`. The unused configured DB never existed; disposable adapter files were under pytest/task-created `/tmp` roots. No drop/reset/delete SQL or production startup was used. The real-auth bridge test uses actual JWT/get_current_user code and overrides only its account lookup with synthetic User objects; it creates no production ORM tables or connection.

Final applicable suite: **406 passed in 57.08 s**, one inherited Starlette/httpx TestClient deprecation warning. Breakdown: 40 lifecycle/HTTP; 30 C3A; 28 admission; 91 C1/C2; 202 existing load/Authored preservation; 15 existing normalized Generated profile checks. Command (explicit isolated environment described above):

```text
python -m pytest -q packages/core-engine/tests/test_customized_admission.py packages/core-engine/tests/test_customized_calibration.py packages/core-engine/tests/test_customized_planner.py packages/core-engine/tests/test_customized_pilot.py packages/core-engine/tests/test_load_intelligence.py packages/core-engine/tests/test_authored_prescription.py packages/core-engine/tests/test_authored_constraints.py packages/core-engine/tests/test_authored_warmups.py packages/core-engine/tests/test_authored_redistribution.py apps/api/tests/test_customized_preview.py apps/api/tests/test_customized_lifecycle.py apps/api/tests/test_customized_lifecycle_http.py apps/api/tests/test_generated_decision_profile.py apps/api/tests/test_generated_training_profile.py
```

Tests cover exact receipts/mode/subject/session/version/terms, missing/forged/expired/replayed challenges, altered retries, one-winner optimistic revision races on independent SQLite handles, full snapshot/history preservation, correction/undo evidence invalidation, immutable dates/DST/week boundary and adjacent context, unknown effort/skill/restrictions, synthetic malicious authority fields, no cross-account object discovery, request/origin/size/error boundaries and no activation even after simulated future positive cryptographic admission. This is not production PostgreSQL concurrency, migration or session-revocation qualification.

## Independent review and browser evidence

Fresh read-only review of immutable `3fe4ef3..0073732` inspected the complete changed source/test scope and direct support. It found three Important issues: omitted work comparison failed open when absent; retained same-week work was excluded; and late browser render could restore a previous account's cleared preview. Parent reproduced all three, added negative tests and corrected them in one pass. The associated Minor button-state issue was corrected through the same centralized UI state update. Follow-up independent review of the correction diff found no remaining Critical/Important issues and independently reran seven added API cases; it did not rerun Playwright. Its remaining Minor dirty-input consistency case was also corrected and verified in the final browser run. Review corrections and final qualification are included in the draft; no claim of scientific or production-host review follows.

`research/m4c3b1/browser_qualification.js` was executed with actual Playwright against only the loopback disposable factory. Desktop 1440×1000: real preview → 20 checks + agreement → accepted → blocked → withdrawn, Withdraw then disabled. Mobile 390×844: preserve prior snapshot → long plan2 at explicit90 cap → decline. No horizontal overflow. It held actual create/render/challenge/accept responses, switched Alice to Bob before releasing each, and confirmed no old preview/terms/controls restored. All four delayed-response cases passed. Invalid JSON in a new revision leaves consent preparation disabled for the old candidate; successful preview/revision alone clears dirty input state. No JavaScript console errors/warnings were reported by the tool; no production browser/account, real device or physiology/time measurement is claimed. Screenshots are optional local artifacts, not evidence hosted on GitHub; the committed browser script is reproducible.

Codex Security diff scan `b627032f-07c6-435b-8c64-ba38eff3eb00` targeted `3fe4ef3..0073732`; capability preflight passed, ten changed source files inventoried and read. The prior-account UI race was recorded as one discovery candidate (CWE-200), with its later correction and browser evidence explicitly outside that immutable scan. **Initial canonical semantic export was rejected**: “Scan output parent must not be group- or world-writable without the sticky bit.” The scan is preserved with context for authorized recovery; no host permission change/bypass, complete/sealed report, SARIF or security pass is claimed. Independent scoped review and focused regressions supply the current limited evidence.

## Honest hosted baseline

PR #90 at stack base `3fe4ef3`, [run 38947930114](https://github.com/Shadowgar/hypertrophyapp/actions/runs/38947930114), completed **failure**. Read once: core **719 passed/4 failed** (same four baseline cases); web **173 passed/1 failed**, ambiguous history-calendar link; API **808 passed/9 failed/25 skipped**. Eight API failures match the prior C1/C2 baseline; the ninth was C3A's `test_adapter_has_no_database_or_file_mutation_during_decisions`: subprocess `ModuleNotFoundError: research` from `apps/api` working directory. This was not labeled an unrelated failure: it was reproduced RED with API cwd/PYTHONPATH and corrected by explicit child repository paths/cwd, retaining every no-I/O assertion; the same reproduction passed GREEN. Documentation/workflow/container checks passed on the base. The inherited test names/fingerprints are retained in [C2 evidence](2026-10-16-m4-c2-full-body-pilot.md#existing-red-hosted-ci-exact-revision-and-basehead-classification).

No costly unrelated full CI rerun/cleanup, production pause or source audit. Current draft hosted status is reported separately at its exact published head; local 406 passes do not make inherited CI green.

## C3B2 decisions only

1. Name the qualified independent reviewer and approve exact versioned science policies, dose/rest/effort/calibration/returning rules and any reduced-work choice with owner signoff; retain qualifications/evidence and operational signing/revocation ownership.
2. Qualify real variants/anatomical metadata, licensing, equipment/load inventory, skill provenance and measurement-informed duration bounds. Current synthetic timings do not promise gym availability or equal/optimal hypertrophy.
3. Authorize the bounded live lifecycle schema/roles/session/CSRF and activation/rollback contract, with qualified #83 scheduling integration and explicit handling of retained occurrences. Then separately qualify real auth/browser/security and PostgreSQL migration/concurrency before enabling any real workout. No such approval is manufactured here; C4 and Military/Hybrid remain separate.
