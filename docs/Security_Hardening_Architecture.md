# Security & Hardening Architecture Contract (Phase 11)

Purpose: define deterministic, self-hosted hardening architecture for secrets handling, rate limiting, backup/restore, and operational failure drills.

## Scope

- Infrastructure and API hardening strategy for Docker Compose deployment.
- Operational contracts that preserve deterministic runtime behavior.
- Validation/drill requirements for reliability and recoverability.

This document sets architecture and contracts. It does not claim all implementation tasks are complete.

## Security Invariants

- Runtime training logic determinism is unchanged by security controls.
- Secrets are never committed to git history.
- Production secrets are injected via environment/runtime secret files only.
- Backups are encrypted at rest and include verification metadata.
- Restore procedures are deterministic, scripted, and testable.

## 1) Secrets Strategy

### Source of truth
- `.env.example` contains placeholders only.
- Runtime values are supplied via host-managed `.env` and secret files mounted into containers.

### Required secret classes
- JWT signing key(s)
- Database credentials
- OAuth/WebAuthn secrets (when Phase 12 lands)
- Optional encryption key material for backup artifacts

### Rotation contract
- Support key rotation window for JWT verification (active + previous key).
- Rotation must not require schema-breaking data migration.
- Rotation procedure must include deterministic rollback steps.

### Forbidden patterns
- Hard-coded secrets in source files.
- Printing full secrets in logs.
- Reusing default/example secrets in production.

## 2) Rate Limiting Architecture

### Objectives
- Protect auth and mutation-heavy endpoints from brute force and burst abuse.
- Maintain normal workout logging usability under expected mobile usage.

### Enforcement layers
- Edge layer (Caddy) for coarse IP-based throttling.
- API layer for route-class policies with deterministic responses.

### Baseline policy classes
- `auth_strict`: login/register/reset endpoints.
- `mutation_medium`: logging/profile update endpoints.
- `read_lenient`: read-only plan/guide/history endpoints.

### Response contract
- Exceeded limits return deterministic `429` with retry guidance headers.
- Logging path should fail fast and predictably under rate pressure.
- No silent drops.

## 3) Backup Architecture

### Minimum backup set
- PostgreSQL logical dump (schema + data).
- Versioned app config snapshot (`infra/`, deployment-relevant env template refs).
- Optional artifacts: generated deterministic docs indices for provenance checks.

### Backup schedule
- Daily incremental retention + periodic full snapshots.
- Retention policy is explicit, versioned, and documented.

### Artifact requirements
- Naming includes UTC timestamp and monotonic sequence.
- SHA256 manifest generated per backup bundle.
- Encryption enabled for off-device storage.

## 4) Restore Architecture

### Restore guarantees
- Restore yields a bootable environment with consistent API schema.
- Data restore is idempotent at the workflow level (rerun-safe scripts).
- Post-restore health checks are deterministic and scripted.

### Required restore procedure stages
1. Provision clean target environment.
2. Restore database from selected backup artifact.
3. Rehydrate runtime config/secrets from secure store.
4. Run migration/status verification.
5. Run smoke checks (auth, plan generation, workout logging).

### Success criteria
- API starts cleanly.
- Core endpoints pass smoke checks.
- Selected checkpoint data is present and consistent.

## 5) Failure Drill Program

### Drill scenarios (minimum)
- Lost primary DB volume.
- Corrupt backup artifact detection via checksum mismatch.
- Secret rotation misconfiguration rollback.
- Rate-limit misconfiguration causing false positives.

### Drill cadence
- Monthly lightweight drill.
- Quarterly full restore drill on clean environment.

### Drill evidence
- Timestamped run log.
- Scenario, duration, outcome, corrective actions.
- Follow-up tasks tracked in docs/plan checklist.

## 6) Observability & Audit Requirements

- Structured security events: auth failures, rate-limit hits, restore events.
- Backup/restore jobs emit machine-parseable status and checksum results.
- Alert thresholds for repeated auth failures and backup failures.

## 7) Implementation Checklist (Phase 11 Execution)

- Add secret-file based runtime configuration to compose stack.
- Add edge/API rate limit policies with route-class mapping.
- Add scheduled backup job + encrypted artifact storage + checksum manifest.
- Add scripted restore flow with smoke checks.
- Add monthly/quarterly drill runbook and record format.

## Change Control

If these contracts change, update in the same session:

- `docs/High_Risk_Contracts.md`
- `docs/GPT5_MINI_HANDOFF.md`
- `docs/Master_Plan.md`

## Progress Sync (2026-03-06)
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

