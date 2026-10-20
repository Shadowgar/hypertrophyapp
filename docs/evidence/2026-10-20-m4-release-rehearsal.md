# M4 disposable migration and recovery rehearsal, 2026-10-20

Scope: release qualification for the active Customized lifecycle candidate, based on `46b57a603499fcb54f8b7e954008aaa5808e321c` plus the named working-tree changes. This is engineering evidence for OPS-001/002/003, HIST and DATA-005 boundaries, not production deployment or whole-milestone acceptance. No production database, personal records, Compose service or production configuration was read or changed.

## Migration entry point and correction

The existing Compose API entry point is `alembic upgrade head && uvicorn ...`. The initial candidate contained two Alembic heads, `0022_authored_load_states` and `0023_customized_inventory`, sharing `0021_selected_workout_dates`. On an owned empty disposable database, the actual `upgrade head` command failed with exit **255**, reporting `Multiple head revisions`. This was an operational dependency defect, independent of prescription policy.

The additive correction is [0024_merge_authored_customized](../../apps/api/alembic/versions/0024_merge_authored_customized.py): a merge revision with both heads as parents and no upgrade/downgrade DDL. Existing migrations remain unchanged; their existing refusal to destructively downgrade retained history remains intact.

| Content | SHA-256 |
|---|---|
| `0022_authored_load_states.py` | `f0b0c0d1d266f2385443f4115054c0f4b67ce3b4d80ea2e35e03548e81098d68` |
| `0022_customized_application.py` | `3c4fce57ed2c67fa755e31cc5e7171773585e7db692df6e09772756d5bfadfd0` |
| `0023_customized_inventory.py` | `8cd09d29acd204626fefeb30aa888a053993bf32ec6d4ff0c3bae3d3c4f5155f` |
| `0024_merge_authored_customized.py` | `ff9da4b4a036efc810943b2c1fa808435ae0142c2fba8530a19c9b4decea9afa` |

## Isolation and actual checks

The existing [provision/bootstrap/open_target harness](../../research/m4c3b2b/README.md) created a unique direct `/tmp/m4-release-rehearsal-20261020-a` root and exclusively owned PostgreSQL **16.13** cluster. Image was the harness-pinned `sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e`; limits were **256 MB, 0.5 CPU, 128 PIDs, 192 MB tmpfs**, random loopback-only port. Each additional database was newly created within that cluster. Before DDL, the rehearsal checked container ID/label/mount/network, exact database/user identity, empty schema and random out-of-band marker. Every process started with `env -i`, explicit paths and an unused disposable SQLite import target; actual PostgreSQL URLs were constructed privately from the verified manifest. No inherited application environment or checkout `.env` was used.

| Check | Actual result |
|---|---|
| Full historical Alembic chain to `0021_selected_workout_dates` | Passed, **3.382 s**. |
| Populate six source tables, then actual `alembic upgrade head` | Passed, **2.933 s**; user, authored plan/snapshot, set receipt, retry command and session state retained exact per-table content digests. **6 rows / 6 tables**, no inferred candidate consent. |
| Repeat `alembic upgrade head` | Passed, **2.693 s**, same source digests; single head `0024_merge_authored_customized`. |
| Fresh chain to `0022_authored_load_states`, populate synthetic user/load evidence, then `upgrade head` | Passed; **15 preexisting tables / 3 rows including marker**, exact digests retained. |
| Fresh chain to `0023_customized_inventory`, populate synthetic user/inventory, then `upgrade head` | Passed; **20 preexisting tables / 4 rows including marker/schema version**, exact digests retained. |
| Real API publication, Today, log, correction, completion/history; actual inventory load increase and correction reconstruction | **2 passed in 15.45 s** on the fully migrated PostgreSQL target, without a temporary clock plugin. |
| Existing logical backup/restore procedure | **22 tables / 95 rows**, **7,332,594-byte** private dump; restored into a new database, exact per-table row counts/content digests equal; **4 proposal histories** hash-chain replayed. |
| Restored application reads | Login, Today, occurrence progress, dated history and retained correction audit all **HTTP 200**; completion **11 sets / 100%**, receipt count unchanged by reads. Synthetic route clocks were explicitly pinned to the fixture date. |

The initial two API population tests failed because their original fixture pinned only the Customized planning clock to 2026-10-19 while Today used real 2026-10-20. These were fixture date mismatches, not migration failures. A private clock plugin first yielded 2 passes in 12.52 s; the main task then fixed the shared fixture's workout/plan clocks, and the final 15.45 s run used that durable fix with no plugin. Both the failed and corrected outcomes are retained here. Existing Starlette and naive-UTC deprecation warnings remain.

Backup restored the earlier populated snapshot, before the final repeated workflow test added more independent synthetic accounts. Exact digests compare the dump's source snapshot with its restored copy, not later source writes. Candidate consent/events/heads/commands, active plan and occurrence snapshots, inventory, original/corrected receipts and retry/session state were all part of the restored tables. No production sample or physiological outcome is represented.

## Commands and retained artifacts

Interpreter: `/tmp/hypertrophy-c3b1-venv/bin/python`; worktree: `/tmp/hypertrophy-m4-c3b2b`. The private task root retains manifests, dump, sanitized chain logs/results, and the exact local qualification scripts `chain_probe.py`, `qualify_chain.py`, `branch_compatibility.py`, `restored_smoke.py`. They are synthetic artifacts, not repository fixtures or a second release system; manifests include synthetic credentials and are mode 0600.

The environment-cleared invocations used `PYTHONPATH=packages/core-engine:apps/api:.`, `PYTHONDONTWRITEBYTECODE=1`, explicit `DATABASE_URL`, `TEST_DATABASE_URL`, `LOG_FILE_PATH`, `PROGRAMS_DIR`, `COMPILED_KNOWLEDGE_DIR`, and for pytest an explicit disposable `CI_TEST_ROOT` and `C3B2B_TARGET_MANIFEST`. Actual module/script arguments were:

```text
python -m research.m4c3b2b.provision --fresh-disposable-root /tmp/m4-release-rehearsal-20261020-a
python -m research.m4c3b2b.bootstrap --manifest /tmp/m4-release-rehearsal-20261020-a/target.json
python /tmp/m4-release-rehearsal-20261020-a/chain_probe.py
python /tmp/m4-release-rehearsal-20261020-a/qualify_chain.py
python /tmp/m4-release-rehearsal-20261020-a/branch_compatibility.py
python -m pytest apps/api/tests/test_customized_application.py::test_real_workflow_publish_today_log_correct_complete_history apps/api/tests/test_customized_inventory.py::test_complete_easy_exposure_gives_attainable_next_load_and_correction_rebuilds -q
python -m research.m4c3b2b.backup_restore --manifest /tmp/m4-release-rehearsal-20261020-a/chain-target.json
python /tmp/m4-release-rehearsal-20261020-a/restored_smoke.py
```

For a new rehearsal, use a new unique root and rebuild/verify its manifests; do not reuse the recorded stopped target. The chain scripts use actual Alembic subprocesses with the verified target URL, not `metadata.create_all` to qualify migrations. Synthetic API fixtures may create missing tables with `checkfirst` on their independently verified target; the recorded chain already supplied all 22 tables.

## Existing operational procedure and remaining boundary

The [existing backup wrapper](../../infra/scripts/backup_postgres.sh) runs a Compose-default `pg_dump` to local SQL. It has no standalone restore wrapper and was **not** invoked: its default service would cross this task's production boundary. The existing [bounded restore procedure](../../research/m4c3b2b/backup_restore.py) runs the same logical `pg_dump` primitive, creates a new database, restores with `psql -X -v ON_ERROR_STOP=1`, checks all table digests and replays candidate histories. That existing procedure was executed unchanged. Private dumps remain outside Git.

Source-defined stack order is healthy PostgreSQL → Alembic upgrade → API process → web; Caddy depends on web/API. Web/Caddy dependency declarations establish container start order, not full application readiness. API's direct Dockerfile command omits Alembic; the Compose command supplies it. Startup still calls `Base.metadata.create_all`; this task does not claim separate runtime DDL-role qualification or sole-writer enforcement.

A future authorized release must integrate the candidate's source/identity/scheduling dependencies, include the merge revision, take and validate the approved backup, run migrations against the explicitly authorized target, verify API readiness, then serve the matching web/API versions and deliberately configure `CUSTOMIZED_ENABLED` (default false). This record changes no deployment setting. Index lock duration, production data volume, operational grants, retention/encryption, owner RPO/RTO and actual production restore/cutover remain unmeasured. Disposable seconds are observations, not production timing guarantees.

The existing history migrations reject destructive downgrade. A rollback must preserve schema and user history; reviewing a compatible earlier application/feature-disable path is separate from executing any release. No release, reverse migration, merge or production rollback was performed.

Cleanup: the exact task-owned container ID/label and resource/network limits were rechecked before `docker stop`; the `--rm` container's removal was independently confirmed. Its tmpfs PostgreSQL data is gone. Private synthetic manifests/dump/scripts/results remain under the task root for local review. An immediate post-stop removal assertion raced Docker's asynchronous cleanup; the subsequent independent check confirmed removal.
