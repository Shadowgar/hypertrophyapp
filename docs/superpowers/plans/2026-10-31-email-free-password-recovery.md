# Email-free recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver isolated-tested operator recovery and an unmerged self-service recovery PR.

**Architecture:** Reuse short-lived PasswordResetToken for private operator issuance. Dedicated hashed backup-code and security-event tables extend the existing server-owned confirmation and credential-bound JWT lifecycle.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Alembic, PostgreSQL 16, React/Next, pytest/Vitest/Playwright.

**Spec:** docs/superpowers/specs/2026-10-31-email-free-password-recovery-design.md

## Global Constraints

- Owner approved design and additive 0028 in PR plus disposable-only rehearsal; no production issuance, migration, write, restart, deployment or release changes.
- Ten independent 256-bit backup codes; operator code expires in ten minutes; hashes only at rest.
- Preserve all accounts, training data, compiler inputs and licensed artifacts.
- Current password and current JWT required for setup/regeneration; consume/reset atomically under User locking.
- Focused development tests; normal final PR-head qualification once. Keep #103/#105 open.

## Review Focus

- Lost secret response: no replay; explicit regeneration or renewed operator authorization.
- Same-password concurrent reset changes salt: stale JWT must fail after account lock.
- Racing generation/reset: one authoritative transaction, no obsolete codes exposed as current.
- Target drift/recording: refuse stale manifests and require private controlling terminal.
- Account switch/unmount: discard late secret response, never persist browser codes.

### Task 1: Current-schema operator issuer

**Files:** scripts/operator_recovery.py, scripts/operator_recovery_worker.py, scripts/tests/test_operator_recovery.py, docs/operations/operator-account-recovery.md.
**Interfaces:** worker `inspect_target(db, user_id)` returns secret-free fingerprints; `issue(db, binding)` locks/rechecks and returns transient token only after commit. Host CLI prepare/issue controls verified Docker/local target and private TTY.

- [ ] Write focused refusal/identity/expiry/invalidation/single-use tests, run red.
- [ ] Implement explicit target manifest with host, container, image, schema, cluster, volume and account binding; private-terminal-only issuance; no production execution.
- [ ] Run focused current-schema SQLite and disposable PostgreSQL tests green; document exact separate issuance authorization.
- [ ] Commit tested issuer and runbook.

### Task 2: Permanent atomic recovery authority

**Files:** apps/api/app/models.py, security.py, deps.py, auth_limits.py, schemas.py, routers/auth.py; new app/account_recovery.py; alembic/versions/0028_account_recovery_codes.py; tests/test_email_free_recovery.py.
**Interfaces:** `generate_codes(db, user, command_id)` and `confirm_recovery(db, token, new_password)` return secret transient codes or status; settings GET status/events and owned event acknowledgment.

- [ ] Write red API tests for ten hashes, password confirmation, duplicate command, generic failures, one-use/remainder, old JWT rejection, event isolation and short-lived reset revocation.
- [ ] Implement additive tables, domain-separated hash, fresh credential check under User lock, atomic claim and audit; retain legacy request/confirm compatibility.
- [ ] Run focused API/security and real PostgreSQL race/rollback tests; rehearse populated synthetic 0027→0028 preserving original rows.
- [ ] Commit API and migration.

### Task 3: Recovery-code browser workflow

**Files:** apps/web/components/account-recovery.tsx, app/settings/page.tsx, app/reset-password/page.tsx, tests/account-recovery.test.tsx, tests/auth.approved.test.tsx; scripts/qualification/email-free-recovery.browser.cjs.
**Interfaces:** existing auth token and API base; POST /auth/recovery-codes, GET /auth/recovery-codes, POST owned event acknowledgment; unchanged POST password-reset/confirm.

- [ ] Write red UI tests for default code journey, generation confirmation, once-only display, stale responses and notifications.
- [ ] Implement transient settings component and email-free reset journey; preserve legacy token URLs.
- [ ] Run focused UI/type/lint and desktop/mobile browser tests on isolated services; no live submissions or secret screenshots.
- [ ] Commit UI and browser evidence.

### Task 4: Final review and PR

**Files:** bounded runbook/contract/traceability updates as necessary, qualification evidence.
**Interfaces:** exact final commit qualified by normal GitHub PR workflows.

- [ ] Fresh whole-diff review and Codex Security diff scan; resolve material findings with focused tests.
- [ ] Confirm no compiler/artifact changes and production untouched; record limitations.
- [ ] Push one feature branch and create one reviewable unmerged PR, then inspect normal final-head checks.
- [ ] Report head, results, operator procedure and exact separate production issuance approval. Save checkpoint.
