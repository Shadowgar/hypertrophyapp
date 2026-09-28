# ADR-006: Load and exposure model

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Persistent progression currently counts work sets as exposures and uses planned state rather than actual logged weight. Actual RPE is normally missing. Load authority is a major owner-requested outcome. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

One completed exposure is a finalized exercise occurrence with effective qualifying work sets and an explicit completeness result. Repeated exercise occurrences are separate exposures. Compare only compatible performed variant/equipment/load basis/units/prescription/effort evidence. Calculate/prefill increase, hold or decrease; monitor explains insufficiency. Mid-workout load correction follows the same authority boundary. Source sets/reps/effort/block structure stay fixed.

## Alternatives and consequences

Per-set counters; arbitrary cross-variant pooling; or exposure-normalized qualified data. Propose the latter without choosing numerical training thresholds. Use a ruleset with declared accepted/proposed thresholds, actual attainable increments and override provenance. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Existing ExerciseState becomes a reconstructible projection, not history authority. Unknown actual effort remains null; prescribed RPE is not a performed observation. Legacy/load units may prevent comparison. New effort/equipment fields are additive only after accepted contracts and migrations.

## Verification and relationships

Actual-load versus planned-load divergence; missing effort, bad-day versus repeated regression, assistance/per-hand load, attainable rounding, correction replay and automatic prefill with override. Confidence conveys sufficiency, not guaranteed gains.

Controlling document: [contracts/load-progression.md](../contracts/load-progression.md). Milestone: M2A. Historical concordance: D-008–D-013; D-018 local deterministic goal. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
