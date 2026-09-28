# ADR-007: Selected-date scheduling

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

The runtime takes day count and server date; authored offsets can become consecutive days. Actual available dates are an original owner purpose and must progress alongside load work. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Initially accept manual current-week distinct local dates and IANA timezone. Allocate all authored units and relationships losslessly; compare previous/next-week context; return feasibility/conflicts. Stable tie-breaking uses versioned inputs. Unstarted reschedule preserves occurrence identity through a new placement revision; started/completed prescriptions are not regenerated.

## Alternatives and consequences

Mechanical count offsets; required external calendar integration; or a simple weekly date picker plus deterministic allocator. Propose the third. No calendar connector is required and M2B does not wait for unrelated M2A work. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Add date/timezone and placement identity after M0-HIST and M1. Legacy server-generated dates are not user-selected dates. Started-work exception and carryover policies need explicit approval. Exact spacing thresholds remain proposed unless grounded in source/doctrine.

## Verification and relationships

Tue/Fri/Sun equals output dates; DST, duplicates, week membership, cross-week neighbors, paired/primer preservation, long sessions and infeasibility; deterministic replay and reschedule history. Never trim authored dose to make dates fit.

Controlling document: [contracts/selected-date-scheduling.md](../contracts/selected-date-scheduling.md). Milestone: M2B. Historical concordance: D-006–D-010; D-021 prohibits deriving customized topology from authored layouts. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
