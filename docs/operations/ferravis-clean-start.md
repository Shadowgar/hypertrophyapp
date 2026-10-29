# FERRAVIS clean-start operation — prepared, not authorized

The owner authorized engineering, a protected recovery snapshot and disposable
rehearsal on 2026-10-29. **No production reset, merge, deployment, restart or
release-control change has been performed or authorized by this document.**
Follow [DB_SAFETY_LOCK.md](../../DB_SAFETY_LOCK.md) and the
[qualified release controller](continuous-release.md). The bounded implementation
is registered in [the prelaunch plan](../plans/ferravis-prelaunch.md).

## Verified target and deletion scope

The preparation baseline is deployed revision
`8693ede061428b5202ca3661092b5d030d372bca`, database/role `hypertrophy`, Compose
project `hypertrophyapp`, service `postgres`, volume
`hypertrophyapp_postgres_data` mounted at `/var/lib/postgresql/data`, and Alembic
revision `0026_initial_calibration`. The full container ID, cluster identifier,
image ID, schema/content fingerprints and snapshot digest are in the private
manifest, outside Git. These are evidence of the preparation target, not approval
to use that old revision for the future reset.

All 23 persistent application tables were inventoried. Counts below are the
preparation snapshot, not a promise that live counts remain unchanged.

| Table | Rows | Action and ownership |
| --- | ---: | --- |
| `alembic_version` | 1 | Preserve migration state |
| `customized_candidate_schema` | 1 | Preserve staging schema state |
| `authored_initial_calibrations` | 0 | Delete; user-owned calibration |
| `authored_load_states` | 2 | Delete; user-owned working loads |
| `body_measurement_entries` | 0 | Delete; user-owned measurements |
| `coaching_recommendations` | 0 | Delete; user-owned recommendations |
| `customized_candidate_commands` | 10 | Delete; subject-owned commands |
| `customized_candidate_events` | 12 | Delete; subject-owned staging history |
| `customized_candidate_heads` | 2 | Delete; subject/event-owned candidate pointers |
| `customized_candidate_sessions` | 3 | Delete; subject-owned staging sessions |
| `customized_equipment_profiles` | 1 | Delete; user-owned equipment |
| `exercise_states` | 0 | Delete; user-owned exercise state |
| `password_reset_tokens` | 1 | Delete; user-owned reset credentials |
| `soreness_entries` | 6 | Delete; user-owned soreness/notes |
| `user_interface_preferences` | 1 | Delete; user-owned preferences |
| `users` | 9 | Delete; account identity, credentials and profile |
| `weekly_checkins` | 4 | Delete; user-owned check-ins |
| `weekly_review_cycles` | 4 | Delete; user-owned review history |
| `workout_log_commands` | 21 | Delete; user/occurrence-owned logging commands |
| `workout_occurrences` | 3 | Delete; user-owned scheduled occurrences |
| `workout_plans` | 12 | Delete; user-owned plans and schedules |
| `workout_session_states` | 0 | Delete; user/occurrence-owned session state |
| `workout_set_logs` | 17 | Delete; user/occurrence-owned performed sets |

The catalog contains 24 foreign keys. Every deletion table reaches `users` through
an inspected ownership path. Customized commands/events/sessions use `subject`;
candidate heads additionally reference the event's subject/proposal/revision.
Workout commands, session state and set logs reference occurrences. Set-log
corrections have a self-reference. The existing authored-load user FK has
`ON DELETE CASCADE`; its child rows are explicitly deleted first. No blind
cascade is used. Unknown tables, cross-scope FKs, custom triggers/rules,
nonordinary relations and unreviewed dependency cycles stop the tool.

Canonical Authored programs and licensed/source provenance live in repository
assets (`programs`, `knowledge`, `docs/rules` and the separately protected source
fixture), not these account tables. The tool runs no DDL, sequence reset,
migration, container/volume removal, configuration edit or source-asset write.

## Implemented safeguards and qualification

[`reset_user_data.py`](../../scripts/reset_user_data.py) accepts explicit targets
only. The former shell entrypoint delegates to it; calling that script with no
arguments cannot reset anything. Production target checks bind the full immutable
container ID, image ID, database, role, cluster ID, Compose identity, exact volume
and matching running API/web revision. Disposable targets must have the explicit
disposable label and only tmpfs mounts.

`prepare` captures schema, per-table counts and SHA-256 content fingerprints,
creates one custom-format compressed dump, then requires the same inventory.
Artifacts are private, created exclusively and never overwritten. `verify-restore`
restores only into an empty verified disposable database and checks all 23 tables.
Three existing preference CHECK expressions have a narrowly allowed PostgreSQL
dump/restore array-cast normalization; all other catalog fields and all content
must match. Production pre-delete catalog comparisons are always exact.

`apply` requires the exact manifest digest and matching successful restore receipt.
Production also requires the exact revision-specific approval string below. It
defaults to a dry run. With `--execute`, it reserves a private audit, opens one
transaction, takes an advisory lock and exclusive locks on all 23 tables, and
rechecks target, schema and every count/content fingerprint under those locks.
It deletes 21 tables in FK dependency order, users last, and checks zero account
rows, unchanged schema and unchanged schema-state records before committing.
Lock/statement timeouts refuse an unsafe or contested attempt. A transport or
post-commit verification failure is recorded as uncertain; never retry blindly.

Actual qualification on 2026-10-29:

- One protected 798,987-byte production snapshot was created and restored into a
  separately verified loopback/tmpfs PostgreSQL cluster. All 23 table contents
  and the narrowly normalized catalog matched. The snapshot and private receipts
  remain under `ferravis-prelaunch-evidence`, outside the repository.
- The PostgreSQL rehearsal proved dry-run preservation, refusal after inventory
  drift, exact rollback after deleting a populated table (two working-load rows),
  and successful deletion of all 21 account tables with both schema-state rows
  and schema preserved.
- A disposable API lifecycle test registered a synthetic account, reset its
  database, and registered the same email again with a different UUID. Old
  credential-bound and legacy JWTs returned 401; the old reset token returned 400.
  New registration worked. The disposable account tables were then emptied.
- Pure guard tests run in normal tooling CI. Real PostgreSQL and API reset
  rehearsals require explicit opt-in receipts/targets and skip in ordinary CI;
  a skip is not a substitute for the actual rehearsal above.

The authenticated onboarding draft format binds answers to the account UUID.
The UI qualification separately tests old-owner and legacy unowned draft rejection.
Neutral guest preferences and the existing date-only soreness-skip key are not
account credentials. For the fresh-owner acceptance test, use a new private
browser context or clear **this application's origin only** from local/session
storage. Keep compatibility key names unchanged. Never clear unrelated sites.

## Future release sequence and separate approvals

1. Approve integration of the two final immutable PR heads, in security then UI
   order. Publishing was enabled and the release timer active at preparation.
   Integration authorization must explicitly cover disabling publishing and
   pausing the release timer before either merge, verifying no executor/request
   is pending, and leaving both controls in the approved state. This assignment
   changes neither control.
2. Merge through normal protected procedures. Require exact resulting main CI,
   the complete private-source/API profile, core, web, tooling, documentation,
   security and container qualification. PR success cannot establish private
   protected-main source fidelity. Resolve review findings before integration.
3. Obtain deployment authorization naming that exact main SHA and allowing the
   existing publisher/timer controls for its automatic release. Use the qualified
   GitHub-to-host controller, never manual image/service replacement. Verify the
   live API/web SHA and immutable images, health, assets and unchanged database
   schema/counts/content before considering a reset.
4. Prepare/reverify the reset against the **new deployed FERRAVIS SHA**, inspect
   fresh counts and verify a compact snapshot on a new empty disposable target.
   The old baseline manifest cannot authorize deletion after deployment. Avoid
   redundant backup accumulation: retain the current verified recovery snapshot
   until a replacement is verified and its retirement is authorized.
5. Obtain a distinct one-time reset approval binding the deployed SHA, full
   PostgreSQL container/image/cluster/database/role/volume, the 21-table scope,
   fresh manifest digest, matching snapshot and restore receipt, maintenance
   window and expected zero-account state. The approval must explicitly permit
   deletion of all existing accounts, credentials and training records.
6. Execute once in the approved window; verify all 21 zero counts and preserved
   schema/state/library/configuration, then perform the separately authorized
   fresh registration/onboarding acceptance test. Keep Issues #103 and #105 open
   for physical-iPhone, gym and performance acceptance. Complete historical
   onboarding questionnaire editing was not included in PR #127 and is not added
   by this assignment.

## Exact command forms for the future operator

These are templates, **not execution authorization**. Obtain every value from the
freshly verified target and reviewed private artifacts, never inherited Compose
or database defaults. Run the tool from the qualified deployed source revision.
Use a private existing directory (0700), new artifact filenames and `umask 077`.
No shell command below supplies a database password or prints personal rows.

```sh
python3 scripts/reset_user_data.py prepare \
  --kind production --container "$APPROVED_PG_CONTAINER_ID" \
  --database hypertrophy --role hypertrophy \
  --system-identifier "$APPROVED_PG_CLUSTER_ID" --image "$APPROVED_PG_IMAGE_ID" \
  --volume hypertrophyapp_postgres_data --app-revision "$APPROVED_LIVE_SHA" \
  --snapshot "$RESET_SNAPSHOT" --manifest "$RESET_MANIFEST"

python3 scripts/reset_user_data.py verify-restore \
  --kind disposable --container "$VERIFIED_DISPOSABLE_CONTAINER_ID" \
  --database "$VERIFIED_DISPOSABLE_DATABASE" --role "$VERIFIED_DISPOSABLE_ROLE" \
  --system-identifier "$VERIFIED_DISPOSABLE_CLUSTER_ID" \
  --image "$VERIFIED_DISPOSABLE_IMAGE_ID" \
  --manifest "$RESET_MANIFEST" --receipt "$RESET_RESTORE_RECEIPT"

# Review dry-run output; the actual manifest SHA-256 must match owner approval.
python3 scripts/reset_user_data.py apply \
  --manifest "$RESET_MANIFEST" --confirm-manifest "$APPROVED_MANIFEST_SHA256" \
  --restore-receipt "$RESET_RESTORE_RECEIPT" --audit "$NEW_RESET_AUDIT" \
  --production-approval "RESET ALL FERRAVIS USERS AFTER DEPLOY $APPROVED_LIVE_SHA"

# Only after separate exact reset authorization: same arguments plus --execute.
```

To rehearse, add `--rehearsal-container "$VERIFIED_DISPOSABLE_CONTAINER_ID"`
to `apply`; this selects only the receipt-bound disposable target. Production
approval does not transfer to another database or revision. Rehearsal consumes
the restored rows; do not rerun it as if that target still contained the snapshot.

Stop on changed identity, image, revision, table/FK scope, catalog, counts,
fingerprints, missing snapshot, failed restore, active deployment, concurrent
user activity or unexpected pending request. The tool changes no ingress or
release control. Arrange any needed maintenance/write-quiescence separately;
exclusive locks protect the transaction but registrations may resume after it.
If a post-commit check observes new writes, inspect the audit and state before
doing anything further. A timeout/disconnection may have an uncertain commit
outcome; neither repeat deletion nor restore automatically.

Recovery is a separately approved operation. Restoring the snapshot restores old
accounts and credentials and can revalidate old sessions/reset tokens; it therefore
requires an explicit session/credential invalidation plan and isolated rehearsal.
Preserve the existing immutable images and controller recovery safeguards.
