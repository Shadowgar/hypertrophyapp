# M4-C3B2B persistence and source integration plan

> Execute inline using executing-plans and test-driven-development. Issue #97 and the direct owner instruction authorize this bounded design, isolated code/tests and one stacked draft; no additional design or publication approval pause applies.

**Goal:** qualify durable inactive candidates, transactionally revocable server sessions and exact-source calendar reads against disposable PostgreSQL. No new generator or preview flow.

**Base/spec:** checked PR #95 `b4e3a3fbd4a3e1f3ed4e7689582d818b40d263c8`; owner review and [Issue #97](https://github.com/Shadowgar/hypertrophyapp/issues/97). Science approval remains separately tracked in #96.

**Architecture:** existing LifecycleService and compact consent remain owners. Make the constructor-supplied authorization callback read-only; the existing factory validates ownership without assigning it. Add a PostgreSQL implementation of the existing proposal transaction interface and an actor-bound transaction seam. Lock existing User first (the same lock as #83/history), then read server-owned session/grant and candidate ledger on that connection. Calendar reads use that same transaction. No production registration, User alteration, runtime migration or active-workout writer.

**Safety:** one exclusively owned 256MB/0.5CPU tmpfs PostgreSQL16 container, random127.0.0.1 port; verify container ID/label/mount/network and explicit DB/user before DDL. Require an out-of-band random marker and exact target allowlist. No inherited URL, existing DB reset, production Compose/service operation or destructive SQL. Additive migration outside the production Alembic chain; fixture creates only named existing source tables before migration. Preserve Authored rows byte-for-byte. Backup restores into a second freshly created disposable DB only.

## Tasks and verification

1. [x] Reproduce callback overwrite with two existing factories/shared service. Read-only constructor callback, reject mismatched factory gate, verify distinct hosts, no gate/default grant and callback reassignment failure. Focused staging/lifecycle tests.
2. [x] RED then implement PostgreSQL target validator, additive ledger/session schema, existing store interface, hash-chain replay and actor-bound User lock. Server-generated UUID session mapped from credential fingerprint; explicit entitlement/scopes/revision/expiry; reset/revoke/rotate use same account lock. Tests: reconnect/replay, rollback/CAS/idempotency, foreign404, two subjects, accept/retry racing reset/revoke/rotation from independent connections, historic retry after withdrawal. No app-wide JWT changes.
3. [x] Exact #83 source read bridge using existing User/WorkoutPlan/WorkoutOccurrence/WorkoutSetLog/WorkoutLogCommand/WorkoutSessionState identity/history. Pinned #83 remains unmerged; source_verified remains false. Tests: previous/current/following weeks, DST, repeated source/exercise identities, snapshot preservation, correction/undo freshness, account ownership, ambiguous and missing coverage; account-lock calendar edit race. No writes by calendar adapter.
4. [x] Run focused applicable regressions, minimal PG backup/restore and read-only baseline comparisons. Scoped independent/security review without host permission repair. Freeze stack/merge manifest, record actual evidence/limits and short forward/rollback release plan; publish one stacked draft on #95.

## Review focus

- Concurrent revocation must either precede and deny acceptance or follow its completed commit; no post-revoke cached authority.
- A separate subject's lock must not serialize all accounts; callback/connection context cannot leak between hosts/threads.
- Replayed event digests must detect missing, reordered or changed revisions; withdrawn consent stays ineffective.
- Full original consent audit survives the SQL adapter and no unapproved source or science flag can activate workouts.
- Actual source reads must preserve duplicate exercise slots and frozen snapshots even after all effective sets are undone; absent source coverage stays unknown.

## Execution ledger

- Verified #95 and #83 open/unmerged at recorded heads, main27231cf. Known hosted baseline parity from owner review: core719/4, API871/8/25skip, web173/1. Do not rerun broad suites or repair these.
- Fresh owned PG target verified before DDL: PostgreSQL16.13, DB c3b2b97_7b9bdd6dd4, role c3b2b_owner, loopback32768. Source tables and credentials are disposable only.

- Task1: reproduced shared callback overwrite, constructor property + factory ownership check; new ownership2 pass.
- Tasks2/3: final28 PostgreSQL/source/ownership tests passed18.88s. Independent review missing-tail/empty-coverage findings both RED→GREEN; source correction3bc55a2. Full applicable run130pass/one new test expectation corrected, then final28pass; do not claim a full131 green run.
- Task4: final populated-source migration73 rows unchanged; full logical restore12 tables/267 rows and20 replayed proposals exact. Initial160MB restore failed capacity; retained evidence, fresh192MB target under same256MB/0.5CPU limit passed. No preexisting target reset.
- Ruling: full131 rerun not repeated after correcting the one test's longer-candidate audit expectation — unchanged applicable tests already passed; final28 includes corrected test and all changed DB/source behavior. Cost: no single final all-green131 execution; evidence reports separate runs explicitly.
- Scope/evidence: [C3B2B qualification](../evidence/2026-10-17-m4-c3b2b-postgres-integration.md). Source verified remains false; report export remains unsealed. Final step is publication of the prepared stacked draft, no release acceptance.

## PR #98 independent COMMENT correction — authorized follow-up

- Keep the existing PR/branch and C1–C3B2A authority; no new preview system or production change.
- Reconcile pinned #83: a missing/empty neighbor is unknown, not an authoritative rest week. Represent observed database absence per week explicitly; retain incomplete/fail-closed consumer status until the owning scheduling contract supplies authoritative negative coverage. New accounts do not require fake blank plans. Old unbound receipts are ambiguity only if they can intersect current source identity or have receipt/amendment/void evidence at/after the local window start; timestamps are not performed dates.
- RED→GREEN focused coverage cases: new account, empty neighbors, malformed empty dated row, unrelated old legacy, reused source IDs, recent/late amendments/voids and legacy session state.
- Replace lifetime loads with account+week/date/occurrence SQL, retain amendment closure and all voids; group relevant histories by occurrence. Rehearse composite/partial source indexes only on the new disposable copy, not production models/Alembic.
- Measure queries and plans on ~10 years of synthetic history; assert returned/examined source rows remain window-scoped. Record exact counts/timings/EXPLAIN, source-contract differences and hosted failure classification. No broad unrelated suite.
- Follow-up verification:99 relevant tests passed69.75s; scale test passed10.67s. Final read-only measurement7 queries/10 rows/max11 examined scan rows per query;23.94ms large median versus23.10ms baseline. Prior original#98 hosted run classified baseline-only RED (API874/8/50skip,core719/4,web173/1).
- Ruling: do not invent authoritative absence absent an accepted #83 coverage authority. New users/empty weeks get explicit observed-empty evidence while consumer completeness remains false. Cost: live negative-coverage admission remains unresolved; no fake-plan workaround or weakening of source trust.
