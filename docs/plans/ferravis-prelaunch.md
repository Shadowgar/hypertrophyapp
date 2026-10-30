# FERRAVIS pre-relaunch implementation plan

> For agentic workers: implement each owned package with focused failing/passing tests, then independent review and final qualification. Use the executing-plans workflow for the reset package and parallel specialists for security and UI.

**Goal:** Prepare two qualified, unmerged PRs for runtime/security remediation and FERRAVIS branding with two bounded UI repairs, plus a rehearsed account-data reset procedure.

**Architecture:** Keep the existing API/core/web architecture and release controller. Use immutable patched runtime images, preserve public/storage/auth/service compatibility identifiers, and implement the reset as an explicitly targeted offline operator transaction with complete table coverage and protected recovery evidence.

**Tech stack:** ARM64 Docker, Node 24 / Next.js, FastAPI/Python, PostgreSQL 16, Caddy, Playwright and the existing CI/security toolchain.

**Spec and authority:** Owner's October 29, 2026 FERRAVIS pre-relaunch assignment authorizes engineering, safe qualification, read-only production inventory and one protected recovery snapshot. It explicitly withholds merge, deployment, production reset, release-control changes and live restarts. This bounded plan records that assignment; historical Proposed ADRs do not supply extra authorization.

## Global constraints

- Preserve live revision `8693ede061428b5202ca3661092b5d030d372bca`, production records, schema/configuration, release safeguards and immutable images throughout this assignment.
- No more than two PRs: security/runtime and UI/branding. Reset safeguards belong with security/operations; no third reset PR.
- Retain Authored Phase 1/2 and Customized decision authority, source fidelity, deterministic algorithms, consent and date/occurrence semantics.
- Public brand is **FERRAVIS — Strength, Engineered.** Original geometric iron/F mark; existing approved interface and theme families remain the foundation.
- Do not rename repository, domain, tables, routes, services, environment variables, storage keys or auth identifiers.
- No destructive production test. All reset/write tests use verified disposable targets and isolated settings; no inherited database fallback.
- Issues #103/#105 remain open; physical iPhone/gym/performance acceptance remains separate.

## Review focus

1. A cache, stale JWT or draft belonging to a deleted identity must not bind to a newly registered identity with the same email.
2. A newly added table/FK/trigger, changed schema, wrong database/container/cluster, changed data or missing restore receipt must abort reset before deletion.
3. A transaction failure must leave every user-owned record intact, while successful reset preserves both schema-state tables and source artifacts.
4. A short viewport, on-screen keyboard or save failure must keep modal actions and error/pending state reachable without background scroll/focus escape.
5. Runtime/image and security findings must be qualified for actual ARM64 contents; unverified CVE claims and skipped tests must remain explicit.

## Task 1 — Security/runtime package

Owner: security specialist; files include `apps/web/Dockerfile`, applicable dependency locks and verified auth/security boundaries, plus a concise report under `docs/security/`.

- [x] Verify main/live versions, image identities, release controls and available storage read-only.
- [x] Resolve the requested Node/PHP advisories from primary sources, confirm actual version/Brotli/architecture and pin a verified patched multi-architecture Node 24 image in all stages.
- [x] Complete Codex Security source audit, dependency/SBOM/container scans and existing provider finding review; distinguish applicability and uncertainty.
- [x] Write meaningful reproductions for confirmed source vulnerabilities; apply bounded fixes and verify PostgreSQL/session/account negative cases.
- [x] Run native ARM64 production build/runtime checks and publish reproducible security evidence with exact versions/digests.

## Task 2 — Reset preparation and safeguards

Owner: parent; modify `scripts/reset_testing_user_data.sh`, add `scripts/reset_user_data.py`, tests in `scripts/ci/tests/test_user_data_reset.py` and `apps/api/tests/test_clean_start_reset.py`, and `docs/operations/ferravis-clean-start.md`.

Interface: explicit Docker container ID, database name/role and cluster identity; `prepare` generates a private manifest and one protected custom-format snapshot; `apply` requires the exact manifest digest, successful isolated restore receipt and explicit operator approval. Default invocation and inherited environment variables never select a target or authorize deletion.

- [x] Inventory production container/image/volume/database/cluster and all public tables/FKs without exposing personal records. Baseline: 23 tables, 21 account-owned; preserve `alembic_version` and `customized_candidate_schema`.
- [x] Write failing negative tests for missing approval, mismatched identity/scope/schema/data/snapshot, unknown table/trigger/FK, and failed atomic deletion.
- [x] Implement private manifest/snapshot handling, explicit allowlist and dependency-ordered `DELETE` statements in one guarded transaction. Do not reset infrastructure, sequences, schema, migration records or canonical source assets.
- [x] Restore the one protected snapshot into a fresh disposable PostgreSQL instance; compare schema-state records, table counts and content digests, recording a hash-bound restore receipt.
- [x] Rehearse reset only against disposable targets, proving zero account-owned rows and unchanged schema-state/source hashes; inject failure to prove rollback.
- [x] Verify old/legacy JWTs and reset tokens fail after reset and same-email registration. Browser old-owner/new-UUID and legacy-unowned draft checks also passed in both engines.
- [x] Document exact future production procedure and authorization, stale-manifest rejection, concurrent-write handling, and recovery without silently revalidating old sessions.

## Task 3 — UI/branding package

Owner: UI specialist; bounded Today dialog, login-specific layout, public branding/metadata/icons/help/email labels and focused tests.

- [x] Capture baseline screenshots and reproduce modal overflow/login spacing on safe synthetic targets.
- [x] Add regression tests; implement bounded modal with independently scrolling body, persistent footer, focus/keyboard/scroll management and visible pending/error state.
- [x] Fix login-only action spacing, preserving other onboarding layouts and password visibility.
- [x] Add original vector branding and favicon/PWA assets; replace public product labels without renaming compatibility identifiers. Record a concise name-collision review without claiming trademark clearance.
- [x] Qualify 1440×900, 390×844, short desktop and landscape; collect before/after screenshots and synthetic full onboarding/program/date-preview/consent checks.

## Task 4 — Final qualification and release readiness

- [x] Review each package independently; remediate material findings before final commits.
- [x] Create exactly two focused PRs with immutable heads; stack UI on the reviewed security package if needed to qualify the combined application without merging main.
- [x] Run applicable full API/core/web/tooling/build/security/container checks. Record private-source fidelity limits honestly: full protected-main qualification remains mandatory after future authorized integration.
- [x] Reverify production versions/images/control state and read-only data preservation; retain one durable checkpoint with exact continuation details.
- [x] Provide sequence: security integration → UI integration → exact-main full CI/security → approved automatic deployment → live/data-preservation verification → separately authorized one-time reset → fresh iPhone onboarding. Publishing is currently enabled, so integration approval must explicitly cover safe release-control handling before any main merge.

## Qualification evidence and remaining acceptance

Security/runtime candidate `0f028c5c2851a1173ede0e62f334fc7a4a238096` has native
ARM64 image/startup/SBOM/dependency evidence from hosted run `40824500414`.
The web scan reports zero advisories; API runtime installer findings were removed.
Unfixed Debian advisory records remain documented in the security report, not
suppressed or presented as a clean OS scan. Full PR API tests passed at the
combined source `38db151` (1,044 passed, 123 explicit skips; web 526 passed); final heads retain
independent CI checks. Core: 882 passed. Tooling: 123 tests, one explicitly opt-in
PostgreSQL rehearsal skipped in ordinary CI; the actual private reset rehearsal
was separately completed on restored disposable PostgreSQL.

PRs [#128](https://github.com/Shadowgar/hypertrophyapp/pull/128) and
[#129](https://github.com/Shadowgar/hypertrophyapp/pull/129) are the two packages.
Chromium and WebKit passed all four viewports on production-built `38db151`,
including keyboard-sized viewports, pending/error/retry, focus and draft isolation.
Both also passed real disposable-API registration, Authored setup/date preview and
Customized disabled/consent/premature-activation boundaries. Applicable final-head
CI remains a required check on each PR; completion is recorded in the PR status
and durable closeout rather than inferred from earlier runs. A hosted production-mode browser artifact uses a fixed disposable
API endpoint; its receipt distinguishes this configuration from normal builds.
No production-host build is needed. Runtime source equivalence must be recorded
for any later documentation-only head changes.

On October 30, public API/web and main remained `8693ede`; all 23 production
table counts/content fingerprints and catalog matched the protected snapshot.
Images and last production deployment `7377635557` were unchanged. Publishing
remained true, timer enabled/active, executor inactive, and no recovery marker
was present. An interactive operator scheduled a host reboot during browser
qualification; the disposable fixtures were rebuilt and the affected checks
rerun. This assignment performed no host or live-service restart. Issues #103
and #105 remain open. Complete editing of historical onboarding questionnaire
answers was outside PR #127 and is not added by these PRs.

No merge, live deployment, production deletion or release-control operation is authorized by this plan.
