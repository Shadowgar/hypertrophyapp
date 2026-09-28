# Architecture decisions

Status: active decision registry under the owner-approved documentation integration basis; detailed technical mechanisms remain Proposed. Decision context: 2026-09-28. This index does not accept the detailed ADR mechanisms.

## Lifecycle and approval

Use permanent three-digit IDs (`ADR-001`) and four-digit filenames (`0001-...md`). Never renumber an accepted or referenced record; allocate the next unused ID. **Proposed** requests review; **Accepted** names the product/technical decision approvers and exact scope; **Superseded** points to a named accepted successor while preserving rationale; **Rejected** preserves the proposal and reason. Append a dated amendment or successor rather than rewriting accepted history.

Product owner approval governs user authority and desired outcomes. Technical approval governs mechanisms, compatibility and migration. Implemented, verified for a revision/environment and owner-accepted release are separate fields, not ADR statuses. ADR-004 contains an explicitly owner-approved principle dated 2026-09-28, while the ADR remains Proposed because its enforcement mechanisms have not been accepted. Never backdate that approval to D-005.

Each ADR includes context, alternatives, proposed decision, consequences, compatibility/migration, evidence needs and relationships. A superseding proposal identifies affected IDs, callers, data and documents; only explicit acceptance activates supersession. Documentation approval does not authorize runtime changes, migration, deployment or publication outside the authorized branch.

## Proposed records

| ID | Decision | Product/technical state |
|---|---|---|
| [ADR-001](0001-documentation-authority-and-change-control.md) | Documentation authority and change control | Technical proposal; review pending. |
| [ADR-002](0002-mode-authority-and-consent.md) | Authored versus Customized authority and consent | Technical proposal; review pending. |
| [ADR-003](0003-authored-source-immutability-and-compilation.md) | Authored source immutability and compilation | Technical proposal; review pending. |
| [ADR-004](0004-deterministic-runtime-and-ai-boundary.md) | Deterministic runtime and AI boundary | Principle owner-approved 2026-09-28; mechanisms Proposed. |
| [ADR-005](0005-training-history-identity-and-correction.md) | Training-history identity and correction | Technical proposal; review pending. |
| [ADR-006](0006-load-and-exposure-model.md) | Load and exposure model | Technical proposal; review pending. |
| [ADR-007](0007-selected-date-scheduling.md) | Selected-date scheduling | Technical proposal; review pending. |
| [ADR-008](0008-recommendation-evidence-and-overrides.md) | Recommendation evidence and overrides | Technical proposal; review pending. |
| [ADR-009](0009-production-schema-and-data-authority.md) | Production schema and data authority | Technical proposal; review pending. |
| [ADR-010](0010-account-recovery-and-auth-lifecycle.md) | Account recovery and authentication lifecycle | Technical proposal; review pending. |

## Historical concordance

The [ledger](../DECISIONS.md) retains its original IDs and 2026-03-20 last-updated context. All D-001–D-022 remain discoverable; no new ADR silently replaces them. [Governance](../governance/constitution.md) explains the historical milestone boundaries.

| Historical decision | Related proposed ADRs | Retention / unresolved treatment |
|---|---|---|
| D-001 | ADR-003 | Original canonical reference corpus preserved. |
| D-002 | ADR-003 | Guides stay build-time diagnostics. |
| D-003 | ADR-003/004 | Raw references excluded from runtime. |
| D-004 | ADR-003/004 | Compiled runtime artifacts retained. |
| D-005 | ADR-004 | Older no-paid-LLM text retained; stronger 2026-09-28 principle separately approved. |
| D-006 | ADR-002/003 | Authored first-class identity preserved. |
| D-007 | ADR-002 | Existing authored/optimized_generated keys need explicit consent mapping. |
| D-008 | ADR-002/004/006 | Doctrine, policy and engine stay distinct. |
| D-009 | ADR-002/004 | Policy cannot violate hard constraints. |
| D-010 | ADR-002/007 | Hard constraints remain distinct from preferences. |
| D-011 | ADR-002 | Visible fallback/infeasibility must not enable unauthorized authored changes; formal interpretation pending. |
| D-012 | ADR-005/006/008 | Bounded adaptation retained. |
| D-013 | ADR-005/006/008 | Sufficiency and scoped safety exception retained. |
| D-014 | ADR-002 | Full Body v1 scope retained. |
| D-015 | ADR-002 | Wider splits remain deferred. |
| D-016 | ADR-001/009 | Original milestone restriction retained; no perpetual implementation ban inferred. |
| D-017 | ADR-003 | Foundation seeding retains temporary context; no permanent authority inferred. |
| D-018 | ADR-004/008 | Local/offline compiled goal retained; offline writes unqualified. |
| D-019 | ADR-002/003 | Generated originality retained. |
| D-020 | ADR-003 | Temporary compatibility fields named/traced; removal separately reviewed. |
| D-021 | ADR-002/007 | Anti-copy topology safeguard retained. |
| D-022 | ADR-002/003 | Source program IDs remain exercise-level provenance/ranking only. |

The owner authorized documentation integration on 2026-09-28. [Successor classifications](../audits/2026-09-28-documentation-migration-registry.md), the scoped manifest and ledger notice now establish the branch read order without accepting ADR-001 or any other technical mechanism. The original ledger body and date remain unchanged. Acceptance evidence follows the [evidence policy](../evidence/README.md).
