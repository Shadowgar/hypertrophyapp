# SEC-S1 implementation and live key cutover

Record: **SEC-S1-20260928**. Date: 2026-09-28 UTC. Status: **Implemented and verified for the recorded S1 scope/environment**; no whole-release owner acceptance. Operator: Codex acting on the owner's explicit source, key-cutover and activation instructions. Environment: the owner's self-hosted development server, Docker Compose project `hypertrophyapp`, live PostgreSQL retained; verification through the local ingress. [Registered plan](../plans/urgent-account-recovery.md).

## Revision and authorization

| Item | Recorded value |
|---|---|
| S1 source head | `33da45146a1b7cb8bcf2bd54125daddb6e87da4b` |
| Source PR | [PR #38](https://github.com/Shadowgar/hypertrophyapp/pull/38) |
| Merge and activated API revision | `250a0912adccb509024bc3f06a057831d4eb382b` |
| API activation/start time | 2026-09-28 12:52:43 UTC |
| Implementation approval | Owner's separate S1 instruction on 2026-09-28; recorded in PR #38 and its authorization-thread reply. |
| Key/activation approval | Owner explicitly approved replacing the live placeholder key, rejected compatibility with it, and accepted session/reset-link invalidation. |
| Release/ADR boundary | ADR-010 remains Proposed; S2, whole M0-SEC and whole-release acceptance are not complete/accepted. |

The owner explicitly permitted merging despite the documented baseline/fixture CI failures, provided no new S1 P0/P1 regression existed. Both original P1 threads were resolved, current-head Codex review completed with no new P0/P1, and the only open item was the non-blocking quick-start P2 below. No check/workflow or branch-protection configuration was changed, and auto-merge was not enabled.

## Procedure and results

| Procedure / boundary | Observed result |
|---|---|
| Current-head focused API/security/observability/key-isolation tests | 54 passed in the cleared, guarded disposable SQLite checkout. Both inherited-key regressions fail with the old setup and pass with unconditional test-key assignment. Inputs were byte-compared with the immutable source head before merge. |
| Recovery UI tests | 2 passed with network denied. |
| API/core/web/types CI failure comparison | Exact failing identities/messages match the prior S1 head; no new S1-specific failure. Current API: 495 passed, 8 failed, 7 skipped; core: 364 passed, 4 failed; web: 53 passed, 1 failed; types: the same 102 diagnostics. |
| Other scoped checks | Classification, web lint/build, container build, CodeQL and GitGuardian passed; documentation/tooling inapplicable and skipped. CI qualification remains failed because applicable baseline failures remain. CodeRabbit/Copilot skipped review, not substantive approvals. |
| Secure key provisioning | OS-backed cryptographic randomness; atomic replacement of only the JWT entry in the ignored operator environment file, preserving other settings and restricting file access. No key value, partial value, hash or length recorded. Compose resolution and effective running API configuration were checked internally. |
| Effective running signing key | Present; S1 validator pass; known placeholder no. No compatibility with the old placeholder. |
| Image build / isolated smoke | API built from the merge's tracked positive source inputs, excluding environment files, logs, databases and symlinks. Read-only, network-disabled container with tmpfs SQLite and synthetic key passed startup, health, credential-free request, fake-mail reset and login controls. |
| Live activation | Only API recreated; health version equals the merge revision and startup completed. The normal Compose API image tag also points to the active image. PostgreSQL, web and ingress identities/start times were unchanged. |
| Normal startup / migrations | Model and migration files matched the prior running API. Existing startup retained its Alembic/head and table-check behavior; startup logs showed no migration upgrade step. No S1 schema change or destructive migration. |
| Non-account live smoke | API health, homepage, reset-password page and request using a fresh random nonexistent address all returned 200. Response was exactly the generic accepted/null-credential acknowledgment. No real-account reset, mail-delivery claim or production test data was created. |
| Old-session signature check | A synthetic JWT created and signature-verified under the pre-cutover key was held only in process memory. After activation, the protected profile endpoint rejected it with 401 `Invalid token`, establishing signature rejection before account lookup. No real user session or token was inspected. |
| Cutover logs | Startup/smoke Docker output and newly written application-log content were inspected internally for old/new signing-key, SMTP-password and synthetic-probe-token values; none were found. No raw log content or credential was published. This is a bounded scan, not whole-log/security coverage. |
| Data preservation | No live database wipe/reset/reseed, user/history deletion, destructive migration or unrelated service rebuild. The pre-existing unstaged log modification was preserved and excluded from commits. |

Reference CI: [current-head run](https://github.com/Shadowgar/hypertrophyapp/actions/runs/36410425341), [previous-head run](https://github.com/Shadowgar/hypertrophyapp/actions/runs/36406191650). The API's eight failures comprise the six audited behavior expectations and two workbook fixture/path failures. The four core failures, web calendar query ambiguity and 102 test-global type diagnostics remain separately tracked baseline problems. No assertions were weakened, skipped or repaired to qualify this cutover.

This is a sanitized operator record. Local focused/build/smoke outputs and source-only helpers used temporary restricted operator storage; no credential-bearing raw artifacts are published. CI links retain runner evidence subject to GitHub retention. This record does not claim an immutable sealed security export, all-ingress TLS/rate coverage, real mailbox delivery, PostgreSQL race qualification, backups/restores, every real-session outcome or absence of older compromise.

## Invalidation and remaining scope

Existing JWT signatures under the replaced key are invalid by design; users must sign in again. Pending reset-token hashes made with the prior key no longer resolve under the current design. This follows the owner-approved cutover; token rows/history were not deleted. The synthetic signature check supports the JWT effect. Pending old reset-link invalidation follows the key-dependent digest implementation and was not tested against a live account.

SEC-S2 remains unimplemented/unqualified: account auth/session revocation lifecycle after later resets; atomic reset consumption/password update/revocation; isolated PostgreSQL concurrency qualification; auth-version migration and separately approved versionless-token rollout; distributed abuse controls across the real ingress paths. A one-time signing-key cutover does not implement these per-account lifecycle controls.

**Deferred documentation cleanup:** Codex P2 [“Add signing-key setup to the quick start”](https://github.com/Shadowgar/hypertrophyapp/pull/38#discussion_r4121173501). Explicitly deferred by the owner on 2026-09-28 and recorded in the thread; left open rather than marked fixed. No quick-start documentation change or further S1 cleanup loop was undertaken.

Next actual application-development package: [M0-HIST occurrence, retry, undo and correction integrity](../plans/M0-history-integrity.md). Prepared for review only; no M0-HIST runtime work was performed during this cutover.
