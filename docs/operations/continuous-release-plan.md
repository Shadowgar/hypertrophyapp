# Bounded continuous-release implementation — 2026-10-24

Owner task: restore approved WorkoutApp release and make qualified code-only main
updates automatic. This is one focused operations change, not product planning.
Baseline main: `59d541cb569a059bc11fd27414793e1efe377bc4`.

- [x] Read-only host/ingress/images/schema/main/CI inspection.
- [ ] Implement/test release-request qualification and fixed host executor; reject
  PRs, unprotected/stale main, missing/skipped/failed checks and schema changes.
- [ ] Add a public web version response and explicit no-DDL API startup mode.
- [ ] Qualify exact immutable matched images and executor failure/recovery behavior
  in isolation; retain a private, tested backup/restore preflight.
- [ ] Publish one focused PR with tests and exact first-release authorization.
- [ ] Only after authorization: migrate 0024→0025→0026, cut over exact reviewed main,
  install/activate fixed operator-owned worker, and prove one qualified code-only update.

## Chosen mechanism and boundaries

GitHub CI qualifies full main; a workflow_run job independently checks those jobs
and CodeQL, creates a GitHub release deployment request and waits for matching
public API/web versions. A host timer pulls only authenticated GitHub HTTPS
metadata for the fixed public repository; it accepts requests only from GitHub
Actions for protected current main and revalidates actual CI/jobs. There is no
inbound webhook, arbitrary remote shell, new Tailnet credential, general Docker
runner, private registry or production-file synchronization. GitHub uses its
short-lived GITHUB_TOKEN; the host needs no GitHub write credential. Operator-owned
fixed configuration/executor is the local privilege boundary. Candidate code
cannot replace that executor or the existing production Compose files referenced by integrity-checked paths.

Only tracked build inputs from the verified SHA enter a positive-list context;
private backups/source fixtures/logs/env are excluded. API/web immutable image IDs
and revision labels must agree. Preserve actual running environment, including
CUSTOMIZED_ENABLED=true and signing/DB configuration. No automatic Alembic or
startup DDL. Changed migrations stop for explicit backup/restore/migration review.
A failed cutover stops for operator recovery by default. Automatic restoration of
the prior matched images additionally requires an operator-approved compatibility
setting and unchanged schema; never downgrade or restore an old dump over later writes.

Acceptance: negative qualification tests, command/target/no-DDL/immutable-pair tests,
actual isolated images/health checks, fresh CI and bounded security review. Existing
fixture access is limited to protected main. Following the owner's 2026-10-25
instruction to remove recurring fixture approvals, main's full suite runs
automatically; PRs receive no private fixture and cannot qualify a release.
Operator service installation,
production schema changes and app cutover await one exact authorization. No claim
of live automatic-release acceptance before the harmless post-authorization trial.
