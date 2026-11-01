# Email-free recovery qualification — 2026-10-31

Scope: implementation only, base `88bb339fc820e59973fc20666ea00423f43f73fa`.
No production token issuance, password/data changes, migration, service restart,
deployment, merge or release-control action. Issues #103/#105 remain open.

## Isolated evidence

- Synthetic-only PostgreSQL16 on loopback55439, tmpfs512MiB, memory512MiB;
  no production mounts/credentials or restored owner data. Broad focused API,
  migration and existing auth lifecycle/security suite: **62 passed**. After
  legacy-token-prefix compatibility fix, targeted API/issuer suite: **14 passed**;
  expanded issuer suite: **7 passed**, including private-display/uncertain-response
  and two-issuer one-winner cases. Counts overlap; they are not unique-test totals.
- Additive populated synthetic0027→0028 rehearsal: all25 original tables retained;
  all24 non-Alembic table record inventories and original column definitions match.
  Original `customized_candidate_schema` state unchanged; Alembic advances0028;
  two new recovery tables begin empty. No historical backfill or credential rewrite.
- Immediate utility compatibility: exact deployed ARM64 API image
  `sha256:d5f22b73ca993b897004e42d1c58892ffd1801013cdf3f918697911b00d7dd29`
  run as a separate read-only disposable container sharing only the synthetic
  PostgreSQL network. Schema remains0027; existing confirmation endpoint accepts
  the operator code once, rejects replay, rejects old JWT and preserves synthetic
  account preferences and plan. Worker digest
  `6dc6a2caf4f70cdd43c0bae9fadaef44a9c5a1e42d37d72532eb60ca99eaea1f`.
- Focused React/security tests: **9 passed**. TypeScript: no errors. Focused ESLint:
  zero errors; two existing ref-cleanup warnings in login. Documentation check:
  no new broken active links;28 historical baseline exceptions remain.
- Real-browser isolated Next/API: Chromium1440×900 and Chromium mobile390×844.
  Ten codes displayed once; no browser-storage secrets; dismissal hides codes;
  recovery succeeds; fresh-password UI login succeeds; remaining count9; old JWT401;
  replay400; zero page errors; no email sent. Border/layout assertions pass.
  No screenshots/traces with codes visible. WebKit cannot launch due missing host
  libraries; no OS package changes made. This is not physical iPhone acceptance.

## Independent review

Fresh whole-branch functional review at `d91e2c00dd26daa71a5337389e681507af7abf24`
identified one stale email-first security-test suite. Both tests were observed red,
updated while preserving anti-reflection/legacy-body checks, then nine focused UI
checks passed. No other material functional/security defect identified.

Codex Security scan `68e4f85e-ae04-48d4-8de3-a7c020a63ac6` completed/sealed over
`88bb339fc820e59973fc20666ea00423f43f73fa` →
`c9cca60784012e8f38f94069124919ec10a8e33c`: zero findings, all28 changed files
reviewed,16/16 authoritative source items closed, no deferred coverage. Historical
supplied threat model retained with its original scope. A later CSS-token/border
assertion correction was inspected separately; it is outside that sealed range.
No security-sensitive authority changed after the sealed revision. Normal final-head
GitHub CI/CodeQL/GitGuardian results are reported on the PR, separately from local
static review. No OS, live ingress or deployment certification is claimed.

## Remaining gates and operating decisions

Production issuance needs the private [operator procedure](../operations/operator-account-recovery.md),
read-only preparation/verification of a fresh exact target manifest, and separate
owner approval of `ISSUE ONE FERRAVIS RECOVERY CODE <exact manifest SHA256>`.
The owner supplies their new password only to the FERRAVIS confirmation screen.
The utility has not been run against production. Terminal recording detection is
an operator prerequisite, not something isatty can establish. A production display
failure is uncertain issuance and requires renewed authorization, never replay.

Permanent recovery needs separate review/integration and additive0028 migration
and matched API/web deployment authorization. Process-local limiting, localStorage
JWT exposure to XSS, authenticated-settings-only notifications, and no recovery
without a saved code or trusted operator remain explicit limits. No passkeys or
unrelated security/OS upgrades are part of this PR. Existing residual host security
risks and release safeguards are unchanged.
