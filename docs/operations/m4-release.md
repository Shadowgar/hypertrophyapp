# M4 integrated candidate: existing production release procedure

This is the execution handoff for the existing M4 milestone, not a new roadmap or permission to deploy. The owner authorized integration, isolated verification and a release-candidate PR only. **Nothing below has been executed against production.** Issues [#103](https://github.com/Shadowgar/hypertrophyapp/issues/103) and [#105](https://github.com/Shadowgar/hypertrophyapp/issues/105) retain the immediate gym-UX and broader M6 redesign work; this release does not claim to solve them.

## Candidate and prerequisites

The branch starts at current main `27231cfe98631de7eaebf21e13b60c6d145aeeba`. PR heads #86 → #88 → #90 → #93 → #95 → #98 → #100 → #101 → #104 are all ancestors of `7466cfef0a1e02c8deaa7952490a001a61185112`; #83 was already merged locally at `ecca44a` before #100. Advancing the isolated branch to that tree adds 21 existing commits without replaying #83. No main commit is lost. The release PR targets main and is the single integrated candidate; do not merge/cherry-pick all the older overlapping PRs separately.

Use the final reviewed RC SHA as `RELEASE_ID`, not the earlier stack head or an image's mutable `latest` tag. The [release Compose overlay](../../infra/compose.release.yml) extends the existing Compose configuration: both image tags, build versions and OCI revision labels use that same required ID. `CUSTOMIZED_ENABLED` remains false by default. Source numerical policies stay provisional, metadata scoring stays frozen and `source_verified=False` is retained.

Read-only artifact inspection on 2026-10-20 found API `hypertrophyapp-api:issue80-27231cf` (`sha256:31539378274580c2456561e8ea6f837355a55b81409664e1dded76947dd517ed`) and web `hypertrophyapp-web:m2a2-40a10cc` (`sha256:c2cd2a22500b0299bd0af7788741e2844392f91743f1d84aac0dfdc26b2aeb0a`). These are observed artifact identifiers, not proof of the live DB schema or matched source. The production database was not queried. `0022_authored_load_states` is the API source-main head, inferred from its deployed tag; the operator must verify `alembic_version` before any DDL. The external health request was unavailable from this qualification environment and does not establish an outage.

## Explicit authorization required

Before live work, approval must name the final RC commit/PR, production checkout/Compose project and environment file, target database/user, release window and operator. It must authorize the selected merge/integration, private production backup plus isolated restore verification, the additive migration, coordinated API/web replacement, health/readiness probes and deliberate feature enablement. Production-data handling for the backup/restore and any write interruption/index lock window require that same explicit scope. This document grants none of those permissions. Do not inspect secrets, private records or recovery credentials to fill missing fields.

The operator must disposition the recorded inherited red checks using the existing release acceptance procedure; a red qualification job is not a passing release gate. Keep the original test protections and failure logs. Scientific uncertainty is disclosed; an outside scientific reviewer is not an added implementation prerequisite.

## Build and identify the matched pair

Run from an approved isolated checkout at the reviewed RC commit. Keep the previous immutable image IDs available. Use the approved environment file; never print its contents or rendered secrets.

```bash
set -euo pipefail
RELEASE_ID="$(git rev-parse HEAD)"
export RELEASE_ID
# DEPLOY_ENV is the operator-approved absolute environment-file path.
test -n "${DEPLOY_ENV:?Approved environment file required}"
docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml config --quiet
docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml build api web
docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "hypertrophyapp-api:$RELEASE_ID" "hypertrophyapp-web:$RELEASE_ID"
```

Both labels must equal the reviewed SHA. Record both image IDs; tags alone are not immutable identity. API `/health.version` and the web compiled app version must match this SHA after cutover. The overlay is validated without a daemon/database by the focused configuration tests. A build is not deployment or live readiness evidence.

## Authorized target verification, backup and migration

1. Verify the approved Compose project/services, exact DB identity and `alembic_version` using metadata-only queries in the authorized window:

```bash
docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml exec -T postgres sh -ec '
  psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At \
    -c "SELECT current_database(),current_user" \
    -c "SELECT version_num FROM alembic_version ORDER BY version_num"
'
```
 Do not assume checkout defaults or a tag proves schema. Rehearsed starting heads and actual qualification are recorded in the [migration evidence](../evidence/2026-10-20-m4-integrated-migrations.md). A different live head is a stop condition requiring a matching disposable rehearsal, not permission for an improvised migration/reset.
2. Use the existing [backup procedure](../../infra/scripts/backup_postgres.sh) with the approved target/user; its default values are not proof of target identity. Ensure the destination is an owned private non-symlink directory before invoking it, with `umask 077`. Retain a nonempty dump, SHA-256 and source schema/image identity in the approved protected location; no production backup belongs in Git or a PR. Restore that exact dump into a newly verified, separately isolated private PostgreSQL target, and check schema, counts/integrity and representative account/history reconstruction without exposing records. The existing [disposable restore procedure](../../research/m4c3b2b/backup_restore.py) qualifies synthetic data only and must never be pointed at production to evade its allowlist. Owner retention/encryption and RPO/RTO apply to real backups; synthetic timings do not qualify production volume.
The explicit-target form of that existing logical-dump/restore procedure is below. `BACKUP_PATH` must be a new file in the approved owned/private directory. The restore variables must identify a separately verified empty disposable target, never the live PostgreSQL service; handling a real backup there requires the production-data authorization above.

```bash
umask 077
: "${BACKUP_PATH:?New private backup path required}"
test ! -e "$BACKUP_PATH"
(set -o noclobber
 docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml exec -T postgres sh -ec '
   exec pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"
 ' > "$BACKUP_PATH")
test -s "$BACKUP_PATH"
sha256sum "$BACKUP_PATH"
# Only after independent container/DB/user/empty-target verification:
docker exec -i "${RESTORE_CONTAINER:?Verified disposable container required}" \
  psql -X -v ON_ERROR_STOP=1 -U "${RESTORE_USER:?Verified disposable role required}" \
  -d "${RESTORE_DATABASE:?Verified disposable database required}" < "$BACKUP_PATH"
```

3. After backup/restore verification and authorized lock/cutover preparation, run the migration using the **new API image** without starting the old application against a partially upgraded schema:

```bash
docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml run --rm --no-deps api alembic upgrade head
```

The main-head route is `0022_authored_load_states` → sibling `0022_customized_application` → `0023_customized_inventory` → `0024_merge_authored_customized`. From the inventory branch, the missing Authored load branch is applied before the merge. `0024` has no DDL; prior migrations retain data. Do not `stamp` away missing migrations, downgrade retained history, recreate tables or reset volumes. Verify the resulting single head, expected indexes and valid/ready index state. Existing index creation can lock tables; production duration and timeout/window choices require real-volume/operator qualification rather than extrapolation from the disposable fixture.

## Coordinated startup and acceptance

1. Set `CUSTOMIZED_ENABLED=false` in the approved deployment configuration for the initial cutover. Confirm the effective value without printing other secrets. Start the matched pair with no rebuild:

```bash
docker compose --env-file "$DEPLOY_ENV" -f docker-compose.yml -f infra/compose.release.yml up -d --no-build api web
```

Compose's API command repeats `alembic upgrade head` before Uvicorn; the repeat was rehearsed as idempotent. API startup still calls `metadata.create_all`; this candidate does not establish separate production runtime/migration roles. Do not change role grants or topology silently. Existing healthy PostgreSQL and Caddy remain the source-defined dependencies; container start order alone is not application readiness.

2. Probe the approved ingress `/api/health` with a bounded timeout, require `status=ok` and exact API version, then fetch the web and verify its compiled app version/assets. Use the actual approved ingress/ports; the source quickstart's `18080` is not a verified live port map. Check readiness without private logs/record dumps. Use approved release smoke accounts to verify login, both Authored phases, Today, retained history and correction/undo; do not generate/change a real user's plan as a health check.
3. Only under the explicit feature-enable authorization, set `CUSTOMIZED_ENABLED=true` and recreate the API with the same reviewed image, then verify the expected enabled response under a freshly authenticated smoke account. Legacy tokens lacking the new credential/session claims require sign-in before Customized; they are not retroactively converted into consent. Exercise preview/inventory/acceptance/activation/date/replacement flows using designated smoke data only. Existing Authored plans and records must remain unchanged.

## Recovery without erasing history

The qualified first recovery is **the same matched candidate artifacts with `CUSTOMIZED_ENABLED=false`**. Recreate only API configuration as authorized; preserve the upgraded schema, plans, receipts and immutable event history. This blocks new Customized lifecycle/inventory commands while existing shared Today/progress/logging/correction/history paths remain available for already accepted workouts; the isolated recovery test records the exact supported scope. Disabling the flag does not restore retired legacy Generated writers or relax consent/session checks. Legacy Generated users without an accepted original Customized plan cannot create a new one while the feature is off. `/customize` links may lead to an unavailable feature while disabled; that is an acknowledged limitation, not permission to redesign this task's UI.

Do not automatically roll binaries back to the old API: it lacks the new Customized interpretation and credential-bound session behavior. Do not run destructive Alembic downgrade, restore an older production dump over newer logged work, or delete/supersede plans to recover. A broader binary/data rollback requires separately verified compatibility and explicit authorization accounting for every record written since backup. The disposable restore proves recoverability of its snapshot, not lossless rollback of later production writes.
