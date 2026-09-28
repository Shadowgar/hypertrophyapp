# ADR-008: Recommendation evidence and overrides

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

Existing traces and CoachingRecommendation previews are useful but do not form a typed acceptance/decline/edit history. Advice currently risks overstating comparability and permission. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Version recommendations with action, evidence IDs, rule/context version, sufficiency/uncertainty, allowed mutation scope and deterministic explanation facts. Record accepted/declined/modified outcomes and chosen value/reason. Authored load may auto-prefill; that is not retroactive explicit acceptance. Substitution and design changes still need their distinct consent. Outcome review references later comparable observations.

## Alternatives and consequences

Ephemeral text; a single opaque optimization score; or typed evidence/action/outcome records. Propose typed records, preserving explanations and permissions independently of AI wording. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Do not reinterpret existing previewed/applied rows as explicit acceptance/rejection. Preserve legacy origin/status. Audit trails need retention/privacy choices; prompts or prose never become authoritative training inputs.

## Verification and relationships

Evidence resolves to effective records; stale corrected evidence invalidates/recomputes advice; decline/modify persists outcome; advisory diff performs no authored write; automatic prefill can be overridden without losing prescription/history.

Controlling document: [contracts/recommendations.md](../contracts/recommendations.md). Milestone: M2A / M3 / M5. Historical concordance: D-008–D-013 and D-018; new detail not historically accepted. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
