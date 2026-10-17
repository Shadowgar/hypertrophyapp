# C3B2B PostgreSQL/source integration evidence — 2026-10-17

Authorized scope: [Issue #97](https://github.com/Shadowgar/hypertrophyapp/issues/97), owner review on [PR #95](https://github.com/Shadowgar/hypertrophyapp/pull/95). [Architecture](../architecture/customized-postgres-integration.md), [plan](../plans/m4-c3b2b-postgres-integration.md), [frozen dependency manifest](2026-10-17-m4-c3b2b-manifest.json).

Base **b4e3a3fbd4a3e1f3ed4e7689582d818b40d263c8** (#95); reviewed initial implementation3e324bc5724951131d857ecce0f913b30e5df575; corrected source3bc55a2984217cb1fee50bd158b9e901cc1e4a46. Final published head/tree are pinned in the draft PR. No new preview/generator, UI change, program/source audit or training policy activation.

## Actual disposable targets and schema

Local image `sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e`, **PostgreSQL16.13 aarch64**, role `c3b2b_owner`. Final fixture: database **c3b2b97_278a7d58f6**, **127.0.0.1:32769**, fresh owned container with explicit scope label/ID;256MB memory,0.5CPU,128PID limit,192MB tmpfs data. No persistent volume or production bind mount. Connection identity and random out-of-band disposable marker verified before schema or fixture operations. PostgreSQL target comes solely from an explicit private `/tmp` manifest, never inherited DATABASE_URL.

The first fixture (c3b2b97_7b9bdd6dd4 at loopback32768) used160MB tmpfs. Its populated-source migration rehearsal preserved397 rows, but full restore failed **No space left on device**. That is retained failed evidence, not a successful restore. Only that task-owned container was stopped. A fresh final fixture used192MB tmpfs under the same256MB/0.5CPU resource limits; no existing service was restarted/paused or inspected for private data. No destructive SQL/reset helper ran.

Final bootstrap copied only six named existing source tables into the empty, verified fixture. Five additive candidate relations implement schema version, explicit sessions, event snapshots including complete consent, persisted revision/digest heads and command receipts. Migration SQL remains outside production Alembic and does not ALTER existing source/User tables. No production migration was prepared for automatic execution.

## Measured results

| Check | Actual result |
|---|---|
| Final PostgreSQL/source/factory ownership tests | **28 passed in18.88s**, one existing Starlette/httpx warning |
| Applicable lifecycle/HTTP/staging + admission/Authored subset | **130 passed,1 failed in226.79s**; failure was a new test's wrong assumption that longer candidate has20 applicable terms. Corrected to verify retained old20, new summary12 changes/six alternative conflicts; that test and all new SQL/source/ownership cases pass in final28. No remaining reproduced failure in changed behavior. No full131 green-run claim. |
| Earlier expiry/scope/revision negative cases |3 passed after correcting a missing test-only SQL helper import |
| Final populated-source additive migration | **73 source rows in six source tables unchanged**, five additive candidate tables, all original source digests equal |
| Final logical backup/restore | **12 tables,267 rows, all table digests equal**,20 candidate histories hash/head-validated after restore; plain dump21,235,521 bytes, private temporary artifact |
| Source DB / separate migration / separate restore |c3b2b97_278a7d58f6 / c3b2b97_migration_cbb46f4d0d / c3b2b97_restore_a27cc656b4; all in the same owned disposable cluster |

Initial adapter debugging exposed missing fixture ORM-created timestamps, PostgreSQL UUID canonicalization/parameter typing and a test import omission. These were corrected locally; they are not inherited CI failures. Owner-reviewed hosted baseline at #95 remains **core719/4; API871/8/25skip; web173/1** in workflow39054464985. No unrelated expectations or quality gates were repaired. New draft hosted results are reported separately; PostgreSQL-specific tests skip there unless an explicit verified target manifest is supplied.

## What the tests actually establish

- Existing JWT signature/expiry/current User ORM lookup against disposable PostgreSQL, with a separately issued server UUID session. No session/entitlement →403, revoked/expired/credential/revision changes →401 as applicable, missing scope →403; unknown/foreign candidate →404. A token fingerprint is not the session ID or source of scopes. Constructor callback ownership rejects a mismatched host gate and cannot be reassigned through the public property.
- Candidate/consent/command rollback and reconnect/replay, stale CAS, two concurrent distinct commands with one winner, same-key duplicate acceptance with one receipt, two subjects proceeding independently, forged summary/version/protocol negatives through inherited tests. Missing-tail query simulation cannot restore an earlier accepted state because replay checks the persisted head. Corrupt revision rollback leaves the original state intact.
- Independent PostgreSQL connections race acceptance with password reset, grant revoke, credential rotation and calendar edits. The test observes the competing writer waiting on a database lock before allowing acceptance to finish. A separate retry/revoke race checks historical responses under that same lock; later revoked retries deny. No broad global-session revocation claim: production login/reset/provisioning hooks remain unregistered.
- Actual source-table projection across previous/selected/following weeks and DST, duplicate exercise occurrence IDs preserved separately, snapshot/frozen date/revision protection, retained effective/void/undone-command freshness, owner filtering, missing/empty coverage and ambiguous active source rows. Read projection leaves source payloads unchanged. Snapshot remains started after all its sets are undone; missing effective sets do not make it planned.
- Existing compact single acknowledgement retains the shorter candidate's **20 individual terms,12 reductions,six unapproved band conflicts**, full immutable comparison/time evidence. Revising to the longer candidate retains historical short consent but clears effective consent, changes summary hash and requires a new acknowledgement. Backend preserves reverse comparison differences and alternative assumptions. No consent or valid session can create active workouts.

The restore proof is logical synthetic-data recovery, not physical/PITR, production-size, encrypted retention, restricted-role or operator RPO/RTO qualification. Migration/restore produced fresh databases only, with no preexisting database overwritten. Dumps/private target manifests contain synthetic credentials only and are not committed/published.

## Actual source integration and stack order

Checked #83 is still **OPEN/unmerged** at3f4927b3cdcca1e8655337b30b93894741bfca9c. Its selected-date command and shared history owner lock existing User first; active/superseded plan payloads, placement revision and execution snapshots are the concrete source authority. The new adapter reads those actual table shapes/identity helper against disposable copied rows. It does not import/copy the unmerged next-week resolver or claim an authoritative production coverage decision. **source_verified=False stays fixed** and outer scheduling remains unverified. #83 files, current Authored scheduling/history, main/auth/models/routers/web/migrations are unchanged.

Dependency sequence for later review/integration (not merge authorization): main → C1#86 → C2#88 → C3A#90 → corrected C3B1#93 → C3B2A#95 → this C3B2B. Research#84 supplies provenance, not live policy authority. #83 is a separate branch from main; qualify its integration before source verification, reconciling exact source pins and current/next-week/coverage semantics. Rebase/merge conflicts require named consumer checks. Science#96 is a separate approval stream, not another code/preview package.

## Independent/security review and limits

A fresh bounded reviewer read b4e3a3f..3e324bc and reproduced two Important defects without application/DB access: missing final withdrawal event detection, and empty source plans claiming completeness. Both were reproduced RED in isolated tests and fixed in one pass (head CAS/FK and validated coverage), then the new28-test set passed. The reviewer also found the test import omission; no other Critical/Important finding was reported. Final fixes were test-verified, not independently re-reviewed. No minors were deferred.

Codex Security preflight3passed, Daybreak access **granted / Daybreak Blue**. Managed scan **08cdc202-f194-4acb-b635-d7207ae4206c**, initial immutable range above,10 source inventory items. Semantic export again rejected **“Scan output parent must not be group- or world-writable without the sticky bit.”** No permission repair or alternate canonical report was attempted. Scan remains resumable/unsealed; no security-clearance claim. Later provisioning/migration rehearsal helpers and final fixes have implementation/test review evidence, not sealed scan coverage.

## Remaining release requirements and actual owner decisions

Technical work before real routing/activation: accepted #83 source/coverage/current-next-week integration with lock-participating writers; production session issuance/rotation/reset/revocation and explicit entitlement hooks; reviewed production migration/roles/privacy/retention/backfill and production-shaped recovery/concurrency checks; actual account/device/history/scheduling qualification and completed scoped security acceptance. This candidate demonstrates the transaction/source design; it does not install those live hooks. Science/catalog/inventory/real equipment/skill/effort/time approval remains absent.

Nontechnical decisions: complete the bounded qualified scientific/owner review in #96 (including short/long tradeoffs); choose who provisions/revokes opt-in access and the session/consent retention and legacy-session cutover policy; explicitly accept any known baseline CI risk for inert stack integration, and separately authorize each merge/migration/deployment/activation. No professional approval has been invented, and pending science has not blocked the isolated engineering.
