# ADR-005: Training-history identity and correction

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Program-index workout IDs repeat across weeks. Log retries duplicate, state updates race, and undo rebuilds session state while leaving ExerciseState stale. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Propose additive program-version/plan-revision, workout-occurrence, exercise-occurrence and logical-set identities. Distinct repeated source slots remain distinct even with equal exercise IDs. Bind idempotency to user/occurrence/request and normalized payload; atomically persist record and applicable derived state. Corrections/voids retain an audit trail and deterministically reconstruct affected state.

## Alternatives and consequences

Application-wide event sourcing; audited relational edits plus projections; or current mutable counters. Prefer the smallest auditable relational design that passes retry/concurrency/reconstruction gates; no global event-store mandate. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Legacy workout strings cannot always identify a week. Preserve unresolved mappings and raw records; never fabricate RPE or overwrite completed data. Exact constraints, locking/revision strategy and migration require acceptance plus isolated PostgreSQL rehearsal.

## Verification and relationships

Two weeks never share progress; duplicate request returns same logical set; changed retry payload conflicts; concurrent distinct writes survive; correction/undo rebuilds the same load state; repeated exercise slots stay distinct.

Controlling document: [architecture/data-model.md](../architecture/data-model.md). Milestone: M0-HIST. Historical concordance: D-006–D-007 and D-012–D-013 constrain retained history/consent; no historical decision selected a global event store. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
