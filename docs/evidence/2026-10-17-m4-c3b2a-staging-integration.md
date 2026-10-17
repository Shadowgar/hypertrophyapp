# M4-C3B2A isolated integration evidence — 2026-10-17

Scope: [Issue #94](https://github.com/Shadowgar/hypertrophyapp/issues/94), following the owner review on [PR #93](https://github.com/Shadowgar/hypertrophyapp/pull/93). Base is corrected #93 **`a7fc5f4f5b6fda4e81b6870a74c9c37f1d7af037`**. Implementation/evidence are the bounded diff from that base, not the entire stacked research history. [Architecture and proposed schema](../architecture/customized-staging-integration.md) describe authority and remaining integration gaps.

## Prerequisite: hosted API regression corrected on #93

The formerly absolute `app.main not in sys.modules` assertion failed in a shared pytest worker after unrelated tests imported it. The replacement invokes a fresh child auth probe: it rejects app.main import, database/network connections and file writes, uses the actual verifier with synthetic lookup/transactional proposal port, and positively demonstrates a denied SQLite connection. Ordinary configured database files never appear. The module-only factory import remains separate from the explicitly injected auth bridge.

Seven lifecycle HTTP tests passed normally and seven with actual app.main preimported. Corrected hosted run [39052912226](https://github.com/Shadowgar/hypertrophyapp/actions/runs/39052912226), API job **117455006745**, now records **849 passed, 8 failed, 25 skipped** (405.36 s), replacing the previous 848/9/25 baseline. The new test failure is gone. Remaining failures are the two adaptive catalog tests, two Authored/generated total-set expectations, adaptive fourth-exercise guidance, weekly-review adjustment and two missing Phase 1 workbook/source checks. They were not repaired. Existing core/web failures remain outside this package.

## Actual staged demonstration

Run from the isolated worktree with an empty inherited environment and explicit unused `/tmp` SQLite URLs:

```sh
env -i PATH="$PATH" HOME=/tmp PYTHONPATH=packages/core-engine:apps/api:. \
  PYTHONDONTWRITEBYTECODE=1 \
  DATABASE_URL=sqlite:////tmp/c3b2a-unused.sqlite \
  TEST_DATABASE_URL=sqlite:////tmp/c3b2a-unused.sqlite \
  JWT_SECRET=synthetic-c3b2a-review-only-never-deploy-000 \
  LOG_FILE_PATH=/tmp/c3b2a-demo.log \
  python -m research.m4c3b2a.demo --synthetic-review
```

The runner checks both ordinary/test targets before imports and exclusively creates marked disposable account and proposal files under a new temporary root. It creates only the existing User table, with two clearly synthetic accounts; the actual existing JWT/current-user ORM verifier remains in use through a disposable get_db dependency. Only explicit synthetic grants authorize candidate actions. No production startup, migration, main registration, network database or workout writer runs. The optional loopback UI's exclusive mode-0600 credentials file is local test tooling, not an HTTP credential endpoint or deployable auth feature.

Observed flow:

```text
review_required (plan 1)
→ one compact version-bound acknowledgement
→ accepted_candidate
→ activation_blocked, eligible=false, can_activate=false
→ revised plan 2 (prior consent cleared)
→ declined
```

The CLI reports one consumer acknowledgement, 20 retained audit terms, 12 individual workload changes, six unapproved range conflicts, shorter upper minutes 57.5/59/57.5 versus longer 69/70.5/69. Stale context returns409, foreign ownership404, revoked retry401. Both disposable account rows remain. Acceptance is permission to retain an inactive candidate only.

## Focused qualification

Environment: Python3.13.14; existing FastAPI0.142.1 / Starlette1.7.0 / SQLAlchemy2.0.36 / PyJWT2.15.1 / pytest9.0.3. No dependency changes. Tests clear inherited environment, pin unused ordinary/test SQLite URLs, reject checkout .env and assert the unused ordinary DB file is absent. All writes are exclusively created marked `/tmp` fixtures. No production rows/services/config were inspected or modified.

The applicable subset covers C1 planner/calibration, C2 pilot, C3A admission/preview, C3B1 service/HTTP, new staging boundary, M2A load intelligence, Authored prescription/constraints/warm-ups/redistribution and generated decision/training-profile contracts. The initial implementation passed **426 tests in56.77 s**. A fresh independent review then reproduced a password-reset race: the initial request verifier was current, but the final callback reread only the grant. Two new RED regressions reproduced reset/missing-account acceptance. The correction requires a separate fresh credential-revision callback at every authorization check; a reset during acceptance rolls back the event and command receipt. Final post-correction result: **428 passed in71.89 s**, zero failed, one existing Starlette/httpx TestClient deprecation warning. New staging coverage: **22 passed in17.87 s**. The reviewer read the correction and both regressions, confirmed the Important finding resolved and reported no other concrete Critical/Important issue. Post-fix CLI and desktop/mobile/delayed-response browser replay also passed. The CLI initially rejected an invocation missing an explicit synthetic signing key, as required by existing app auth; the documented invocation supplies only a clearly synthetic review key. No runtime fallback was added.

Documentation checker: zero new active link failures;28 existing baseline exceptions retained. `git diff --check` passed. Final protected-path comparison retains exact base trees for programs, knowledge and docs/rules; production main/auth/models/migrations/scheduling files are unchanged. Hosted checks for the new draft are reported separately; local subset success is not whole-repository CI acceptance.

Behavior coverage includes no-grant403; revoked/expired/credential-changed401; missing scope403; unknown/foreign404; server ownership and strict request schemas; mid-command authorization rollback; calendar preceding/following weeks, DST, stable IDs, latest/void/effective-history freshness, frozen work preservation, source ownership/order and blocked spacing; compact consent protocol/summary/version/expiry/retry/withdrawal; concurrent same-key acceptance; unknown skill/restriction/training state and missing inventory/RIR; actual disposable SQL User lookup.

Playwright checks used the actual loopback API/UI at1440×1000 and390×844. Passed: one unchecked checkbox, visible45/33 comparison, all12 expanded changes and six unapproved conflicts; accept then activation-blocked; revise to plan2/90-minute longer candidate; decline; reverse comparison; no horizontal overflow; dirty inputs prevent consent. Delayed create/render/challenge/accept responses were each released after switching accounts and discarded without restoring the old account's preview or consent. Browser console reported zero errors and zero warnings. Reproducible script: `research/m4c3b2a/browser_qualification.js`. This is synthetic review UI qualification, not live mobile/account/scheduling acceptance.

## Security review limits

Scoped Codex Security preflight: three capability checks passed; current Daybreak advisory access granted (Daybreak Blue). Exact initial implementation range was `a7fc5f4..cd7fa7e`, scan **`2cad5311-8e9a-48e8-b67e-0c1f90fb1ec7`**,14 source inventory items. Managed report export rejected: **“Scan output parent must not be group- or world-writable without the sticky bit.”** Host permissions were not changed. No sealed security report/SARIF or security-pass claim is made. Independent review covers the credential-reset correction as well; review evidence remains bounded to this candidate, not whole-application security qualification.

## Release requirements still open

1. Independently qualified scientific reviewer and owner must approve exact policy/ontology/inventory versions, including shorter-workload tradeoffs; provision reviewed signing authorities/key lifecycle. No numerical policy or synthetic inventory is promoted here.
2. Qualify real exercise/equipment/load inventories, user skill/constraints, effort/calibration and measured session feasibility. The60-minute result is a provisional estimate, not a guarantee or equal hypertrophy claim.
3. Accept and implement production account/session entitlement/revocation, additive schema/retention and transactional lock/replay design; disposable PostgreSQL migration/concurrency/backup/restore evidence; integrate the accepted #83 calendar/effective-history/current-next-week contract and source verification. Preserve existing Authored work and stable occurrence identities.
4. Ordered review/integration of the stack, completed security qualification and actual account/mobile/history/scheduling acceptance, then separate owner authorization for real-workout activation/deployment. No active workout creation or production migration is authorized by this draft.

No broad research, unrelated quality-gate repair, production workload pause, deployment, merge or live-data operation occurred.
