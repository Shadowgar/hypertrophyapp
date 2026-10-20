# M4 integrated candidate: migration, retained history and recovery

Date: 2026-10-20. Application revision: `7466cfef0a1e02c8deaa7952490a001a61185112`, integrated with current main `27231cf`. The added qualification files are identified below. This record is revision-scoped disposable engineering evidence; it does not authorize deployment, migration of production, feature activation, old binary rollback, or release acceptance. No production database or personal data was queried or modified.

## Deployment provenance and remaining preflight

The release coordinator's authorized metadata-only Docker inspection identified deployed API image `hypertrophyapp-api:issue80-27231cf`, ID `sha256:31539378274580c2456561e8ea6f837355a55b81409664e1dded76947dd517ed`, and web image `hypertrophyapp-web:m2a2-40a10cc`, ID `sha256:c2cd2a22500b0299bd0af7788741e2844392f91743f1d84aac0dfdc26b2aeb0a`. This agent did not inspect live application runtime or persistence. Main-source Alembic head `0022_authored_load_states` is the **inferred deployed schema**, not a live-verified schema revision. An explicitly authorized read-only `alembic_version` query and matching artifact/configuration preflight remain required before any production migration. The separate release operations record governs those deployment prerequisites.

## Isolation and procedure

The existing [provisioner](../../research/m4c3b2b/provision.py), [bootstrap](../../research/m4c3b2b/bootstrap.py), [target verification](../../research/m4c3b2b/target.py), and [backup/restore](../../research/m4c3b2b/backup_restore.py) were reused. The new [full-chain runner](../../research/m4c3b2b/full_chain_rehearsal.py) adds a marker-only bootstrap mode, then runs actual Alembic subprocesses against newly created databases. It never uses metadata creation to establish the migration chain. The synthetic premerge Customized workflow deliberately runs without `metadata.create_all`; it therefore exercises the real `0023_customized_inventory` schema before the merge.

Fresh root: `/tmp/m4-integrated-migrations-20261020-c`. PostgreSQL **16.13**, pinned image `sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e`; **256 MB memory, 0.5 CPU, 128 PIDs, 192 MB tmpfs**, loopback-only random published port. Before DDL, verify stored container ID/ownership label/mount/network, exact database/user, empty schema, and random out-of-band marker. The final runner waits for TCP `pg_isready`, excluding the temporary Unix-socket init server.

All invocations cleared inherited environment with `env -i`, used the isolated `/tmp/hypertrophy-c3b1-venv/bin/python`, absolute `PYTHONPATH` entries for repository/core-engine/API, an unused SQLite import target under the fresh root, root-scoped logs/CI paths, explicit repository program/compiled-knowledge paths and a synthetic signing key. Both repository root and Alembic working directory contain no `.env`. Actual PostgreSQL URLs came privately from the verified manifest; manifests/dumps are synthetic private artifacts, not committed configuration. Full reusable command shape is in the [harness README](../../research/m4c3b2b/README.md).

```text
python -m research.m4c3b2b.full_chain_rehearsal --fresh-disposable-root /tmp/m4-integrated-migrations-20261020-c
```

## Full migration and preservation results

Each baseline was built through the complete historical Alembic chain, then populated before `alembic upgrade head`. Every baseline contains separate synthetic Authored Phase 1 and Phase 2 accounts, password hashes, consumed and pending reset rows, plans/source snapshots, dated occurrence/revision identities, immutable original/corrected set receipts, retained retry responses and session projections. Unknown effort stays null. The main-source head also contains each phase's existing authored load projection. The Customized branch additionally contains a real registered API workflow with proposal/consent/event chain, activation snapshot, original/corrected receipts and completed history before the missing Authored branch is applied.

| Baseline before upgrade | Existing tables / rows retained | Baseline chain | Upgrade head | Repeat head | Preservation |
|---|---:|---:|---:|---:|---|
| `0021_selected_workout_dates` | 14 / 21 | 5.493 s | 5.336 s | 4.787 s | Exact per-table count/content digests unchanged |
| `0022_authored_load_states` | 15 / 23 | 5.634 s | 5.340 s | 5.202 s | Exact per-table count/content digests unchanged |
| `0023_customized_inventory` | 20 / 60 | 6.382 s | 5.591 s | 5.469 s | Exact per-table count/content digests unchanged |

Counts include the disposable marker, and exclude the intentionally updated `alembic_version`. The older Customized branch count also includes its existing schema-version row. Every path reaches the single head **`0024_merge_authored_customized`**; repeat upgrade succeeds without source changes. The merge revision itself performs no DDL. No migration files were changed by this qualification.

Actual main-head upgrade order is `0021` → `0022_customized_application` → `0023_customized_inventory` → merge with already-present `0022_authored_load_states`. From the Customized head, Alembic adds `0022_authored_load_states`, then merges. From `0021`, both sibling branches are applied before merge. There is no destructive downgrade/reset or inferred consent backfill.

All three targets contain **12 expected source-read/cohort indexes**, including composite user/week/date/occurrence indexes, legacy-only partial indexes, and `(user_id, program_id, scheduled_date)` load-cohort index. Their definitions are checked, including the legacy-null predicate, and all PostgreSQL indexes are `indisvalid`/`indisready`. This verifies additive index construction on these synthetic databases; production lock duration and data-volume timing remain unmeasured.

## Feature containment and restoration

The fully migrated main-head database ran the real publication/log/correction/completion/history workflow, attainable-load/correction reconstruction, and the new [feature-disabled recovery regression](../../apps/api/tests/test_m4_integrated_recovery.py): **3 passed in 17.13 s**. Existing Starlette TestClient and naive-UTC observability deprecation warnings remain.

With `CUSTOMIZED_ENABLED=False` on the **same candidate API**, proposal/options/activation and proposal-consent history endpoints return **404**. Existing activated plan Today/progress, new set logging, exact retries, correction/retry, correction audit and dated workout history continue working. Lifecycle session/event/command counts remain unchanged during containment. The UI may still expose links into disabled creation routes; this is an acknowledged presentation limitation, not a redesigned recovery flow. Disabling creation does not disable all execution of an already activated plan.

The regression uses exact deployed-source legacy JWT claims (`sub` + `exp`, no `jti`/`cv`): shared reads remain accepted, while fresh Customized entry requires a new sign-in. Newly issued credential-bound tokens are rejected after changing that synthetic account's password; fresh login works with the feature disabled. Legacy versionless/credential-unbound compatibility still exists, including after password changes. This is **not** full legacy-session revocation or qualification of Proposed auth-version/S2 recovery mechanisms.

The unchanged logical backup/restore harness restored into a newly created database: **22 tables / 104 rows**, **5,653,386-byte** private synthetic dump; every table's count/content digest matched and **3 proposal histories** replayed. Consumed/pending reset state, Authored phase separation, source lineage, original/corrected receipts, retries, active Customized snapshots, consent and inventory are included. On the restored database with Customized disabled, login, Today, occurrence progress, correction audit and dated history returned **200**, options returned **404**, and all table digests remained unchanged by reads. These are current integrated results, not counts reused from the prior rehearsal.

Preferred containment is the matching candidate API/web with creation disabled, preserving the upgraded schema and performed history. Returning to the deployed older API is **not qualified**: that verifier does not enforce new credential binding and that application lacks the candidate's lifecycle/load/history policy. A backup restore is incident recovery with an approved consistency point, never routine undo that silently resurrects consumed credentials or discards later workouts. No production rollback, restore, key rotation or downgrade was performed.

## Supplemental PostgreSQL regression qualification

The foundational PostgreSQL session/concurrency and index-scale checks used a separate fresh fully migrated cluster, `/tmp/m4-integrated-pg-regressions-20261020-b`, with the same verified image/resource/isolation bounds. TCP readiness preceded marker bootstrap and the full actual Alembic chain to the merge head. Existing tests ran **once** on this target: **23 passed in 54.59 s** (58.971 s including subprocess setup/capture), with one existing Starlette warning.

```text
python -m pytest apps/api/tests/test_customized_postgres.py apps/api/tests/test_customized_source_query_scale.py apps/api/tests/test_customized_inventory.py::test_scoped_load_query_uses_date_index_with_large_old_history -q
```

This covers independent-connection account locking, same-command retries, competing compare-and-swap writers, transactional failure, replay corruption/missing-tail rejection, session entitlement/scope/expiry/revision checks, actual JWT identity bridging, revocation/reset/rotation/calendar changes before accept and racing accept, and preservation of historical consent boundaries. It does not expand the earlier prototype authority or claim live ingress/account-recovery qualification.

The source-scale fixture adds **500 old plans, 1,500 occurrences, 30,000 bound sets, 3,000 unbound sets, 3,000 commands and 3,000 states**. Seven source queries returned **10 rows**; individual plans examined **0–11 scan rows**, using the intended composite/partial indexes. The current account/source window remained identical before/after unrelated old history. Median observed read was **38.411 ms** before and **47.768 ms** after; these observations are not a production latency SLA. The separate **12,000-old-occurrence/set** load query returned no out-of-window exposure and its actual EXPLAIN used `ix_customized_load_cohort_date`; that large cohort was rolled back by the existing test. No planner switches forced index use.

Private artifacts are `postgres-regressions.log`, `source-query-scale.json`, and `alembic.log`; the exact private environment-cleared runner is `/tmp/m4-integrated-pg-regressions-runner.py`. The supplemental cluster was identity-checked and stopped after qualification. Removal was independently checked together with the failed readiness-race target.

## Artifacts, corrections and limits

Private root retains `alembic.log`, `workflow-tests.log`, `full-chain-results.json`, verified manifests and logical dump. Exact tested migration hashes remain those recorded in the [prior migration record](2026-10-20-m4-release-rehearsal.md); the final merge file is `ff9da4b4a036efc810943b2c1fa808435ae0142c2fba8530a19c9b4decea9afa`. The new recovery test hash for this run is `9f1f12a3dd058b746eece58ea66add366ca41f1f971ff27e07640dd1d8193cb5`; bootstrap is `0ead59192e3c79b13462298609dc0d96754a7bcddc0b4bb4a462538f1cc7f2ac`. The final runner adds only the later TCP-readiness and both-working-directory `.env` checks to the migration run's tested runner body.

An earlier fresh run `...migrations-20261020-b` passed its first two baseline paths but failed when API registration rejected the synthetic `.invalid` email domain. The fixture now uses `example.com`; the entire chain was rerun on fresh root `c`. A separate supplemental-regression target `...pg-regressions-20261020-a` hit PostgreSQL's temporary init-server readiness race before bootstrap or migration; requiring TCP readiness corrects that harness race. Both failed task-owned clusters and the successful migration cluster were stopped after matching exact stored IDs/labels, and removal was independently confirmed for the migration roots. No application implementation changed for either fixture correction.

Disposable upgrade seconds do not predict production timings. Production schema identity, grants/runtime DDL restrictions, lock duration, deployed image/config matching, ingress/recovery rate controls, backup confidentiality/retention, owner RPO/RTO, live account recovery and actual cutover/restore remain separate unperformed operational checks. API startup still has its existing metadata-creation behavior; this record does not claim sole-schema-writer enforcement or broader security acceptance.
