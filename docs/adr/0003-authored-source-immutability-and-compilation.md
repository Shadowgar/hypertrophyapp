# ADR-003: Authored source immutability and compilation

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Phase 2’s numeric-only parser omitted five two-set AMRAP rows despite diagnostics. Runtime flattens set-specific targets; internal artifact parity cannot establish source completeness. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Keep licensed original sources unchanged; compile versioned artifacts with source/importer/schema hashes and reconciled diagnostics. Admit all source exercise slots including nonnumeric targets, per-set effort/techniques and relationships. Qualify source → compiled → execution independently. Source updates create a new version, never rewrite completed prescriptions.

## Alternatives and consequences

Treat current JSON as the entire truth; coerce AMRAP to a number; or preserve typed and raw source semantics with stage-by-stage certification. Propose the third; exact schema remains subject to review. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Retain gold bindings, raw source fields and runtime asset paths. A repaired importer does not silently relabel old plans. License-approved fixture strategy and legacy missing-slot treatment must precede migration; do not copy copyrighted workbooks into public docs.

## Verification and relationships

315 Phase 1 and all 310 Phase 2 rows; AMRAP weeks 6–10; every tested field/relationship/order; diagnostics disposition and unchanged source hash. Existing 80 multiset cases alone cannot certify this.

Controlling document: [contracts/authored-source.md](../contracts/authored-source.md). Milestone: M1. Historical concordance: D-001–D-004, D-006, D-019–D-022; D-017’s seed remains temporary. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
