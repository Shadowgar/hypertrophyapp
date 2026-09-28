# ADR-002: Authored versus Customized authority and consent

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Selection convenience and current binding guards do not fully enforce the owner’s programming permissions. Any restriction currently reopens generic authored adaptation. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Authored preserves source prescriptions and relationships; its normal automatic adaptation is working load with evidence and override. A source-approved substitution requires explicit user confirmation and preserves slot/performed-variant identity. Customized design authority requires explicit consent independently of manual/auto selection. Analyze an authored snapshot advisorially without applying design changes.

## Alternatives and consequences

Infer consent from auto selection; use constraints to unlock generic redesign; or store explicit mode/permission transitions. Propose the explicit transition and preview; concrete storage/UI mechanism remains unaccepted. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Preserve authored Phase 1/Phase 2 and generated bindings. Existing accounts require an explicit legacy-mode policy; never infer historical consent. Retain completed prescriptions and prior history across transitions.

## Verification and relationships

Authored restrictions/time/recovery negative matrix; accept/decline substitution; load-prefill-only diffs; mode transition preview; generated paths cannot write authored artifacts. Owner reviews permissions separately from mechanism.

Controlling document: [requirements/product-contract.md](../requirements/product-contract.md). Milestone: M0-DOC / M1 / M4. Historical concordance: D-006–D-010, D-011–D-013, D-014–D-015, D-019–D-022. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
