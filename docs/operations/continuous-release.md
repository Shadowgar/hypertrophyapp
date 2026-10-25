# WorkoutApp qualified main releases

This is the owner's bounded deployment/automation assignment, not another product
roadmap. Implementation and isolated qualification are authorized. Production
cutover, migration and service activation require the exact release authorization
at the end of the preflight. No production deployment is claimed by this document.

## Verified diagnosis — 2026-10-24

- Host `openclaw`, Tailscale `100.66.50.41`, local Docker context `default`.
  This session is already on the target host. Strict SSH to that IP stopped at an
  unknown host key; trust checking was not disabled and no keys were searched.
  Local container identity and public ingress independently identify the target.
- Production checkout `/home/rocco/hypertrophyapp` is at `1327ddd9b52497327965c365c03bdbb07992ae60`.
  Its pre-existing modified `logs/app-debug.log` is runtime work, not a source edit;
  its contents were not inspected or staged. GitHub main was separately verified at
  `59d541cb569a059bc11fd27414793e1efe377bc4` before editing.
- Project `hypertrophyapp`: `hypertrophy-api`, `hypertrophy-web`,
  `hypertrophy-postgres`, `hypertrophy-caddy`. Live API health and independently
  served web login/assets report `d60d9ed413329f575947568c05888546f8d3e6d5`.
  API image `sha256:c308ddf43731a9f19d6c9d1b767cb2966dd690da84497213c4806f6e8d5c7e66`,
  web `sha256:57b0dc4f06de5dbf246118256a575deb42eefede1c2b595a2a3519ae4a6b6d3d`;
  both image OCI labels match that old SHA. Tags/checkouts were not assumed current.
- Database `hypertrophy`, role `hypertrophy`, source Alembic
  `0024_merge_authored_customized`; tables 0025/0026 are absent. The source volume
  is `hypertrophyapp_postgres_data`, not a disposable target.
- Caddy listens on host 18080, removes `/api/` before proxying to `api:8000`, and
  sends other paths to `web:3000`. No routing/edge change was made.
- Effective Customized is **already true**. Existing `.env` and the six Compose
  source/override paths recorded by the running API are retained by path and
  content/ownership/mode fingerprint. No environment contents or credential copies
  belong in the new manifest, Git, logs or artifacts. No M4 activation replay.
- The existing user service manager is running, UID 1000, `Linger=yes`. The operator
  already has Docker access; no new root account, Docker membership or inbound
  access credential is provisioned. Noninteractive sudo is unavailable; this
  implementation uses an inactive, operator-owned **user** service instead.

GitHub had CI/security/dependency workflows and no production release step. The
merged-main API failure at `0796575` was a fixture ref-policy refusal before tests.
Main's later `59d541c` green run skipped runtime jobs for dependency-only changes.
With explicit owner authorization, main now requires PRs, strict CI/CodeQL/
GitGuardian checks, resolved conversations, admin enforcement and no force pushes
or deletion. Exact main fixture access was added with the existing owner-review
protection preserved, then full main qualification was dispatched.

That full run `40085155150` passes API/web/core/container checks but fails docs:
manual dispatch supplied no comparison baseline, reclassifying all **28 existing**
broken links as new. The narrow repair keeps full test selection and uses the
checked-out commit's actual first parent for documentation comparison. It invents
no baseline for an initial commit. Real new link/structural failures still fail;
there is no blanket link waiver or broad link cleanup. The same main docs with
that explicit parent yield 28 existing / 0 new failures. The failed run remains
failed; fresh corrected-head CI is required before release.

### Automatic fixture qualification — owner direction, 2026-10-25

The owner removed the recurring workbook-approval requirement. The workbook is an
offline test fixture, never a WorkoutApp runtime dependency. The environment is
restricted to exact `main`; earlier integration/PR ref exceptions are removed,
and the manual reviewer requirement is removed only after that restriction is
verified. Protected-main review and required checks remain in force.

PR API checks use an unprivileged `public-ci` environment with no workbook secrets.
The two original workbook tests are selected only by the full main profile;
their assertions and source digest remain unchanged. Existing tests that require
other unavailable source fixtures retain their explicit skip status. A green PR
does not certify source fidelity or authorize a release.

Every protected-main push/manual run automatically restores the exact private
fixture and runs the complete API suite. Raw output stays private and the runner
fixture is removed afterward. In addition to all required jobs, the host and
publisher independently require a successful **Complete API and source-fidelity
qualification** step from that exact main CI run. A missing/skipped/failed full
step or a successful public PR profile cannot qualify production. No per-PR
fixture rules or recurring workbook approval requests are part of this process.

## Release mechanism and trust boundary

[`release.yml`](../../.github/workflows/release.yml) acts only on a completed CI
run from this repository's main push/manual event. No PR/fork checkout or artifact
execution. It stays disabled until the owner-authorized
`WORKOUTAPP_RELEASE_ENABLED=true` repository variable is set. GitHub's short-lived
GITHUB_TOKEN can write deployment requests, not server files or credentials.

[`release.py`](../../infra/release/release.py) verifies current protected main,
fixed repository ID, actual CI workflow origin, every required full job (no skip),
and successful default CodeQL analysis provenance. It creates a SHA-bound GitHub
deployment request, then checks public **independent API and web versions**. The
host timer reads only the fixed public repository over authenticated GitHub HTTPS;
its read-only metadata calls need no server GitHub token. A request must belong to
GitHub Actions' fixed actor, environment/task, SHA and numeric CI run. The host
independently rechecks admission and current main after building. A forged request,
stale build, foreign actor or missing check cannot authorize deployment.

No inbound webhook, general SSH key, self-hosted Actions runner, new Tailnet OAuth
credential, registry credential or arbitrary shell. The installed executor and
manifest live outside candidate checkouts with private operator ownership. A
candidate cannot replace that executor. Existing Docker access remains an
operator-level capability; no new principal receives it. Future executor/policy
changes require reviewed installation, not automatic self-modification.

Only positive-listed **tracked** build inputs from the exact Git SHA enter the
build context. Symlinks/hardlinks/parent escapes are rejected. No private workbook,
backup, env, logs or design gallery context. API/web build with the same full SHA;
image labels and immutable image IDs are verified. The runtime Compose command
uses those IDs with the original effective configuration files, reverified for
drift immediately before cutover. Only API/web are recreated with `--no-deps`;
PostgreSQL/Caddy/volumes/flags/signing settings are retained. API entrypoint changes
are refused. No bidirectional production-file sync, source-checkout reset or pull.

Automatic releases never execute Alembic. Their API command is direct Uvicorn with
`SCHEMA_MANAGEMENT_MODE=validate`; startup verifies the packaged migration head,
tables and columns without `create_all`. Existing explicit development bootstrap
behavior remains available. The executor probes metadata before startup. Any
migration/model change, incompatible schema, configuration drift or stale main
stops for operator review. The initial pre-guard source needs its separately
rehearsed bootstrap procedure; it is never promoted to automatic schema authority.

Before schema checks and again before cutover, the executor resolves the exact
Compose environment privately in memory and compares it with the running pair.
Only version and validate-only startup deltas are allowed. Missing prior shell
overrides, credential changes or Customized activation drift stop the release;
values are neither persisted nor printed. Model relocations are evaluated with
rename detection disabled so the original model deletion cannot evade review.

A failed cutover records only a fixed category in private state/journal, and the
GitHub release job fails if the exact pair never appears. Last-success retains
current/previous immutable pairs and SHA. Automatic rollback is **off by default**:
newly written data cannot silently be interpreted by an unqualified old binary.
Only an explicitly operator-approved compatibility setting permits same-schema
previous-image recovery; both schema and readiness are rechecked. Never downgrade,
stamp, reset or restore an older snapshot over subsequent live writes.

A private `recovery-required.json` marker is written **before** replacing either
service. A crash, partial update or failed readiness blocks the same request and
all later requests. Matching image labels alone do not clear this marker. Stop
the user timer, inspect the fixed-category failure and privately retained old/new
image IDs, then perform explicitly authorized forward repair or compatible image
recovery. Verify both public versions, schema, immutable IDs and preserved
configuration before the operator removes the marker and resumes the timer.
Successful deployment alone removes its in-flight marker after writing the
success receipt. A same-revision poll still checks public readiness.

## Fresh private source backup and migration rehearsal

The preflight used a new owned mode-0700 directory under the existing protected
backup location. [`backup_preflight.py`](../../infra/release/backup_preflight.py)
checks source endpoint/DB/user/schema before imports/use, exports a read-only
repeatable-read snapshot, and holds it through custom-format pg_dump. Source rows
and signature values never enter console output. The private dump is mode 0600.
The raw dump, credentials, private metadata and hashes remain outside Git.

That exact backup restored to `workoutapp-release-restore-1024`, a separately
verified PostgreSQL 16 container using the source's exact image ID, **network none,
no host mounts, tmpfs only**, DB `workoutapp_release_restore`. All 21 source public
application tables' row counts/content signatures and columns/constraints/indexes/
owners/grants matched. A newly verified empty target was used; no reset or source
mutation. This is real private backup evidence, separate from synthetic tests.

The exact-main API image then upgraded **only the restored copy**
0024→0025→0026. Every pre-existing table/row and schema definition stayed unchanged;
only `user_interface_preferences` and `authored_initial_calibrations` were added,
both empty. No preference/history backfill, broad cascade or consent rewrite.
Private proof stays with the private backup. Production remains at 0024.

Prepared exact-main images:

| Artifact | Immutable ID |
| --- | --- |
| API `59d541c` | `sha256:a19d178e7cb4cfdbd063887f5fd26457d6791aa8cbe179f9cf5c54d52df98aa6` |
| Web `59d541c` | `sha256:763b045ec6b7065c845a05c36c264de1936403235fafc300d67f84905c9c36f7` |

Both labels equal full `59d541c…`. They are build/rehearsal artifacts, not a claim of
production deployment. An advanced main requires a newly matched qualified pair;
these IDs must not be relabeled as a later release. The full-run documentation
failure above still blocks 59d541c admission through the unmodified release gate.

## Installation, first cutover and acceptance boundaries

The focused implementation PR must qualify and receive owner integration review.
The actual current-main SHA must then be reverified before the **single production
cutover request** names it; do not deploy a stale branch or a failed aggregate.
The final head-linked PR report fills exact source/CI/image identity and acceptance
results. This document alone does not authorize merge or cutover.

After that authorization, the operator runs reviewed `prepare.py` to capture paths
and fingerprints only, then reviewed `install.sh` as existing UID 1000. Installation
is inactive: no timer enable and `enabled=false`. The already-verified linger
setting ensures the user timer survives logout/reboot. Do not change shared host
permissions, SSH trust, production secrets or feature flags.

The one-time cutover must authorize: target host/project/DB, exact qualified main
and image pair, a temporary API write interruption, **fresh** protected dump and
isolated restoration of that exact quiesced snapshot, 0025/0026 with the exact API
image, and coordinated API/web replacement. The earlier online preflight snapshot
is not represented as the final cutover backup or as coverage of later writes.
Never restore a stale dump to recover work logged after its snapshot.

After backup/restore and migrations pass, API/web cut over together. Verify DB head,
immutable IDs/labels, API health SHA, separately served web SHA/assets, public guest
navigation and Customized=true without touching real accounts. Use only read-only
or explicitly designated synthetic smoke tests. If source/main/config drifted or
any check fails, stop before mutation; no ad-hoc migration or flag change.

Enable the fixed worker and GitHub release variable only as authorized. A harmless
qualified code-only health/version update must then traverse the real
GitHub→request→host→pair→public probes path. Record its exact deployed SHA and
last-success receipt. Isolated admission/recovery tests and staged images **do not
substitute for this live automatic-release acceptance**, which remains pending
until cutover authorization and that trial actually occur. Physical-iPhone and
canonical-security limitations remain distinct; no new acceptance waiver.
