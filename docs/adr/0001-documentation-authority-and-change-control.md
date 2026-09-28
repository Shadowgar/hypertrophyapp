# ADR-001: Documentation authority and change control

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Existing indexes prioritize decisions, the old constitution prioritizes Master Plan, and milestone documents prioritize coding order. These competing claims cannot all govern the same change. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Propose the hierarchy in the constitution: owner requirements/safety, accepted product/governance, accepted ADRs, contracts, traceable requirements, descriptive architecture/procedures, plans, and historical evidence. Preserve the original documents until an explicit successor/context migration reconciles their banners. Index navigation is not a second product contract.

## Alternatives and consequences

Keep all competing authorities; silently replace the ledger; or explicitly reconcile and supersede only approved parts. Explicit reconciliation preserves rationale and makes conflicts reviewable. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

A documentation move can break executable rules, packaging and AI reads. Reconcile the 199-file inventory and path consumers, successor notices and context manifest together. Keep docs/rules/** unchanged. No historical checkbox becomes acceptance.

## Verification and relationships

Link/status check; inventory disposition including every unresolved task; context-consumer review; separate owner acceptance of hierarchy. No runtime test is evidence of documentation acceptance.

Controlling document: [governance/constitution.md](../governance/constitution.md). Milestone: M0-DOC. Historical concordance: Historical D-001–D-022 all retained; D-016 and D-017 retain milestone context. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).

## Integration amendment — 2026-09-28

The owner explicitly authorized applying the documentation hierarchy, successor classifications and scoped context on this review branch. That integration has been performed; this ADR remains **Proposed**, and its technical/change-control mechanisms and ledger supersession have not been accepted. See the [migration report](../audits/2026-09-28-documentation-authority-migration.md).
