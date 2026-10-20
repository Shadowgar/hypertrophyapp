# Disposable PostgreSQL qualification

Use an isolated worktree with dependencies already installed, no checkout `.env`, and an empty inherited environment. No production Compose, DB URL or existing database is permitted. Commands below create one new container and private `/tmp` records, not an application deployment. Use a new direct `/tmp` directory each time; no overwrite/reset cleanup helper exists.

```sh
# Run with an interpreter containing the existing API dependencies.
export PYTHONPATH=packages/core-engine:apps/api:.
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=sqlite:////tmp/c3b2b-unused.sqlite
export TEST_DATABASE_URL=sqlite:////tmp/c3b2b-unused.sqlite
export LOG_FILE_PATH=/tmp/c3b2b-review.log
python -m research.m4c3b2b.provision --fresh-disposable-root /tmp/c3b2b-new-review
# Wait for this newly named container to report pg_isready; do not query others.
python -m research.m4c3b2b.bootstrap --manifest /tmp/c3b2b-new-review/target.json
C3B2B_TARGET_MANIFEST=/tmp/c3b2b-new-review/target.json python -m pytest \
  apps/api/tests/test_customized_postgres.py \
  apps/api/tests/test_customized_source_calendar.py \
  apps/api/tests/test_customized_service_ownership.py -q
python -m research.m4c3b2b.migration_rehearsal --manifest /tmp/c3b2b-new-review/target.json
python -m research.m4c3b2b.backup_restore --manifest /tmp/c3b2b-new-review/target.json
```

`provision` fixes the image digest, memory/CPU/PID bounds, temporary data and loopback-only random port. `bootstrap` verifies owned container identity, empty DB, DB/user and marker before create-only operations. Target manifests/dumps are private synthetic test artifacts, never committed. The SQL is not on the production Alembic chain. Schema changes require a fresh rehearsal; never reset an old target to rerun tests. Stop only the exact task-owned container after verifying its stored ID/label; do not operate on application services.

The full environment-cleared invocation and measured limits are in the repository evidence. Real source verification, session/login/reset wiring and runtime activation remain absent.

For the integrated M4 release, use the existing provisioner's fresh-target
guards with the full Alembic rehearsal below. It runs all historical migrations
to each of `0021_selected_workout_dates`, `0022_authored_load_states`, and
`0023_customized_inventory`, populates synthetic retained evidence, upgrades to
the merge head, checks source digests/indexes, exercises registered application
routes, then backs up/restores into another new database and verifies retained
reads with Customized disabled. This is disposable qualification only.

```sh
# Replace the root with a new direct /tmp path on each run. No .env in checkout.
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/tmp \
  PYTHONPATH="$PWD/packages/core-engine:$PWD/apps/api:$PWD" \
  PYTHONDONTWRITEBYTECODE=1 \
  DATABASE_URL=sqlite:////tmp/m4-fresh-rehearsal/import.sqlite \
  TEST_DATABASE_URL=sqlite:////tmp/m4-fresh-rehearsal/import.sqlite \
  CI_TEST_ROOT=/tmp/m4-fresh-rehearsal \
  LOG_FILE_PATH=/tmp/m4-fresh-rehearsal/api.log \
  PROGRAMS_DIR="$PWD/programs" COMPILED_KNOWLEDGE_DIR="$PWD/knowledge/compiled" \
  JWT_SECRET=isolated-api-test-signing-key-not-for-deployment-000 \
  /path/to/isolated/python -m research.m4c3b2b.full_chain_rehearsal \
  --fresh-disposable-root /tmp/m4-fresh-rehearsal
```

The script stops only its identity-verified cluster after success. On failure it
retains that synthetic target for inspection; verify its stored container ID and
`hypertrophy.scope=c3b2b97-disposable` label before stopping that exact container.
It does not qualify old binary rollback, live schema identity, production grants,
index lock duration, backups containing live accounts, or operational RPO/RTO.

For the PR98 source-window correction, bootstrap also qualifies the proposed composite/partial read indexes on these disposable copies. Focused cases are `test_customized_source_coverage.py` and `test_customized_source_query_scale.py`. The scale case inserts roughly ten years of synthetic history and checks actual EXPLAIN/cardinality, without a wall-clock CI SLA. Supply `C3B2B_SOURCE_QUERY_REPORT` as an explicit private `/tmp` JSON path to retain its sanitized measurements; otherwise the test writes no report. Production indexes/negative-coverage authority are not approved by this test.
