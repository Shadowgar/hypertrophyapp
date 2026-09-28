# ADR-004: Deterministic runtime and AI boundary

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. The deterministic prescription boundary is explicitly owner-approved on 2026-09-28; detailed mechanisms are Proposed.

## Context

On 2026-09-28 the owner explicitly approved: core workout/program decisions remain deterministic and auditable; AI may explain, converse, research, summarize, analyze and assist development, but never directly determine runtime training prescriptions. D-005 is older and narrower. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

The product principle is owner-approved on 2026-09-28. Proposed implementation: typed decision inputs including explicit clock/context; versioned rules/artifacts; deterministic replay; permission checking before application. AI output is explanatory/advisory, cannot be consumed as authoritative exercise/dose/load/date/progression output or acquire persistence rights. Deterministic analysis is also subject to evidence sufficiency.

## Alternatives and consequences

Runtime LLM planner; a mandatory total ban on AI assistance; or deterministic prescription authority with optional assistive AI. The owner selected the principle of the third; interface, deployment and enforcement details remain Proposed. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Preserve existing decision families and offline compilation. Do not retrospectively date approval to the ledger’s 2026-03-20 update. No new runtime AI service, paid dependency or inference path is authorized. Any future assistive boundary needs independent data/privacy review.

## Verification and relationships

Same qualified input/version/context → same prescription and trace; code/boundary review prevents AI-derived prescription mutation. Explain-only assistance cannot write a plan; replay tests use an explicit clock. Scientific outcome evidence remains separate.

Controlling document: [requirements/product-contract.md](../requirements/product-contract.md). Milestone: All training milestones. Historical concordance: D-003–D-005, D-008–D-010, D-018; owner approval adds the current stronger product boundary without rewriting them. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
