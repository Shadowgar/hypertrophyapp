# ADR-009: Production schema and data authority

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Compose executes Alembic while API startup calls create_all; destructive validation can inherit ordinary database settings. Basic dump creation is not verified restore capability. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Propose Alembic as the sole production schema writer and a runtime role without DDL authority; startup validates compatibility. Destructive tests require an explicit disposable target plus enforced negative guards before connection/DDL. Backup and isolated restoration are separate controls with owner-approved RPO/RTO. Never inspect personal records to qualify synthetic behavior.

## Alternatives and consequences

Continue shared startup/migration credentials; rely on a new container name; or separate schema/test/operational authority. Propose separation with a gradual reviewed rollout, not an immediate credentials change. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Exact grants/startup migration compatibility, backup encryption/retention and operational ownership require review. S1 recovery can proceed with its minimal safe subset; S2/history changes need independent PostgreSQL migration and recovery evidence.

## Verification and relationships

Inherited production-like targets rejected before destructive operations; isolated upgrade/backfill and compatible restore; runtime DDL rejection; no credentials/personal data in evidence. SQLite cannot qualify PostgreSQL grants/concurrency.

Controlling document: [quality/test-strategy.md](../quality/test-strategy.md). Milestone: M0-SAFE. Historical concordance: D-016 retains historical milestone context, not a perpetual schema ban; no prior entry qualifies production grants. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
