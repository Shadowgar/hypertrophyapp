# M4-C3B2A staging integration implementation plan

> **For agentic workers:** use superpowers:executing-plans inline. Issue #94 and the owner's direct request authorize isolated implementation and a separate stacked draft; no repeated permission gate is needed.

**Goal:** reuse C1–C3B1 for an account/session-authorized inactive candidate with readable comparisons and one exact version-bound acknowledgement.

**Architecture:** first publish the narrow shared-worker test correction to #93. Stack C3B2A on corrected `a7fc5f4f5b6fda4e81b6870a74c9c37f1d7af037`. Extend the existing lifecycle with a versioned compact consent protocol while retaining individual backend terms. An explicit existing-auth bridge requires independently provisioned account/session grants; no JWT auto-grants. A read-only revision projector consumes pinned #83-shaped synthetic calendar records, not production queries. Reuse the existing guarded factory and renderer.

**Spec:** [Issue #94](https://github.com/Shadowgar/hypertrophyapp/issues/94), owner review on [PR #93](https://github.com/Shadowgar/hypertrophyapp/pull/93), [existing lifecycle](../architecture/customized-account-lifecycle.md).

**Tech stack:** existing FastAPI/Pydantic/PyJWT, core dataclasses and test-only SQLite. No dependency change or production schema registration.

## Global constraints

- Activation/eligibility remain false, every policy remains review_required; no science, catalog or inventory promotion.
- No production main/router/model/migration/auth modification, source changes, #83 worktree/file edits, live data reads/writes or services.
- All DB-related imports/tests use cleared explicit disposable targets; no reset/drop/delete. Proposal storage stays in the uninstalled research adapter.
- The app currently verifies JWT sub/exp/current User; it has no qualified global session revocation model. Added staging grants deny by default and revoke only this experimental boundary, not ordinary application tokens.
- #83 remains open/unmerged at `3f4927b3cdcca1e8655337b30b93894741bfca9c`. Synthetic read-port qualification is not final PostgreSQL/date integration.

## Review focus

- Valid JWT without explicit scope/session grant must fail, and revocation must defeat idempotent historical responses too.
- A compact acknowledgement must bind exact summary/version and retain all 12 reductions/6 unapproved-band conflicts, including timing assumptions.
- A new candidate or consent protocol cannot inherit old approval, token or terms.
- Undo/edits/voids must change scheduling freshness without unfreezing started/completed Authored work.
- Delayed old-account responses and dirty input must never restore old preview/consent UI.

## Task 1: account/session and read-only scheduling adapters

Create `customized_staging_auth.py`, `customized_staging_schedule.py`, focused integration tests and synthetic fixtures. Reuse `get_current_user` explicitly. Grants bind actual verified subject/token fingerprint/account credential revision, scopes, validity and enabled state through a server port; no client entitlements. Calendar envelope binds subject/timezone/source revision/window; resolve latest unambiguous placement and retained history revisions, preserve stable IDs, reject frozen prescription/date changes and missing provenance. No DB adapter connected to #83 until accepted integration.

- [x] Write and run RED: unentitled/revoked/expired account/session, account isolation, revised/void calendar, DST, stale context, retained work and ownership.
- [x] Implement minimum adapters; GREEN; commit.

## Task 2: versioned concise consent and realistic comparison

Extend existing lifecycle/model/HTTP/view with a compact v2 command, server summary/terms digest and receipt. Preserve v1 audit/receipts without silently converting them. Build comparison from actual stored candidate/reference responses and immutable source assumptions; show all three days, 45/33 sets, upper estimates69/70.5/69 versus57.5/59/57.5, all twelve set reductions, six unapproved proposed-range conflicts and limitations. One affirmative acknowledgement covers complete summary; no scientific approval inferred.

- [x] RED: missing/wrong/stale summary/protocol/version/challenge, full audit preserved, hard45 and long hard60 still fail, no active prescriptions.
- [x] Implement same service owner/factory with no alternate generator; guarded UX; GREEN; commit.

## Task 3: isolated staged demonstration and qualification

- [x] Real existing JWT/current-user code with disposable account lookup, explicit session grants, marked proposal SQLite, read-only synthetic calendar source. Show preview/compare/one acknowledgement/blocked/revise/decline and revoked/foreign/stale negatives.
- [x] Focused C1–C3B1/load/Authored regressions only; actual desktop/mobile/delayed-account browser checks.
- [x] Independent scoped review and appropriate security tooling; disclose unsealed export limitation without changing host permissions.
- [x] Propose minimal additive PostgreSQL ownership/revision/receipt/schema/replay design without a production migration. If no disposable PostgreSQL is available, record qualification missing; don't discover/connect to live DB/services.
- [x] Exact manifest, tests/new failures/pending integration and release requirements; publish stacked draft only (publication is the final transport step; evidence is prepared).

## Execution record

Prerequisite fixed on #93 at `a7fc5f4`: fresh-interpreter auth probe rejects app.main import, DB/network connections and writes. Seven HTTP tests passed normally and seven with actual app.main preimported. Baseline failures unchanged. Work executes inline with one fresh final reviewer per applicable execution/review skill.

Final implementation evidence: [C3B2A qualification](../evidence/2026-10-17-m4-c3b2a-staging-integration.md). Scoped428 tests pass after independently reviewed credential-reset rollback correction; synthetic browser/demo pass. PostgreSQL and live integration remain pending; security report export is unsealed.
