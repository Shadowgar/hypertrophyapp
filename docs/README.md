# Documentation and planning review baseline

Owner review context: **2026-09-28**. The owner approved the overall product/documentation direction subject to explicit substitution/load/date/link corrections, and approved the deterministic-runtime/AI prescription boundary. Detailed mechanisms/ADRs remain **Proposed**; no release milestone is owner-accepted by this package.

Application evidence revision: `df9965232ce731f8234d222acc526a90bc6be620`. First published documentation baseline: `311dc00b5a8c97f5df4f0f33188303d27bbdfc91`. This review branch changes documentation only; current-source descriptions are not deployed-image certification.

## Governing direction and decisions

| Document | Purpose |
|---|---|
| [Product contract](requirements/product-contract.md) | Authored/Customized consent, confirmed substitutions, automatic working-load authority and actual dates. |
| [Constitution and working rules](governance/constitution.md) | Proposed precedence, owner/technical approval, retained decision history and safe work. |
| [ADR index and ten proposed records](adr/README.md) | Durable alternatives/compatibility/verification, including newly approved deterministic principle and D-001–D-022 concordance. |
| [Requirements catalog](requirements/catalog.md) | 80 stable desired outcomes/proposals with current state and acceptance needs. |
| [Traceability](requirements/traceability.md) | All 80 IDs linked to product/ADR/contracts/modules/limited tests and missing qualification. |
| [Milestone roadmap](roadmap/milestones.md) | Independent M0 packages; M1 fidelity; parallel M2A load and M2B dates; M3–M6 intelligence/reliability. |

## Architecture

| Document | Purpose |
|---|---|
| [Target system](architecture/system.md) | Component/dataflow ownership without a rewrite mandate. |
| [Current state](architecture/current-state.md) | Revision-scoped runtime paths, defects/limits and original test baseline. |
| [Domain model](architecture/domain-model.md) | Program/slot/occurrence/set/exposure/recommendation vocabulary and lifecycle. |
| [Data model](architecture/data-model.md) | Existing records, additive identities, correction/units/time and migration choices. |
| [Runtime authority](architecture/runtime-authority.md) | Today versus target decision owner, mode/input/mutation/trace boundaries. |

## High-risk training contracts

- [Authored source](contracts/authored-source.md): original/compiled provenance, full fidelity and known AMRAP omission.
- [Execution plan](contracts/execution-plan.md): preserved prescriptions, consent, occurrence/revision and effective history.
- [Load progression](contracts/load-progression.md): completed comparable exposure, actual effort/load, actions, uncertainty and override.
- [Selected-date scheduling](contracts/selected-date-scheduling.md): manual local-week dates, relationships, spacing, reschedule and infeasibility.
- [Recommendations](contracts/recommendations.md): evidence/permissions, automatic prefill versus explicit outcomes and advisory no-write behavior.

## Security, testing and evidence

- [Security architecture](security/architecture.md) and [threat model](security/threat-model.md): source-established versus conditional/unknown/proposed/qualified controls.
- [Urgent recovery brief](security/urgent-account-recovery.md) and [implementation plan](plans/urgent-account-recovery.md): independent S1 closure/S2 lifecycle; no live action authorized.
- [Test strategy](quality/test-strategy.md): isolated targets, meaningful categories, PostgreSQL boundaries and failure disposition.
- [Evidence policy and migration registry](evidence/README.md): artifact basenames/hashes, original results/limitations and stable-retention plan. Original audit artifacts remain outside Git and are not linked as publicly accessible files.

## Status, provenance and integration

Separate owner-approved desired requirement, Proposed technical mechanism, Implemented, Verified for a named revision/environment and release Owner-accepted. ADR lifecycle is Proposed/Accepted/Superseded/Rejected. A partially implemented component or historical pass does not qualify a complete criterion. The explicit AI boundary approval is dated 2026-09-28, not retroactively assigned to D-005; no detailed implementation consequence is automatically accepted.

This package consolidates content ownership without editing competing legacy governance, the [historical ledger](DECISIONS.md), [context manifest](context/CONTEXT_MANIFEST.yaml) or executable `docs/rules/**`. Later approved integration must reconcile all 199 inventory rows, open tasks, provenance/licensing, successors and path consumers in code/tests/workflows/packaging/AI instructions. Update indexes/context references together. Architecture/operations plans not authored here remain deferred, not empty placeholders.

Use repository-relative links; every added repository reference must resolve from another checkout/GitHub. Large/private/proprietary raw artifacts are not copied to fix inconvenient paths. Pinned SnakeTracker [index](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/README.md) and [decision-freeze discipline](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/adr/0028-architecture-governance-and-decision-freeze.md) remain process references studied in the audit, not architecture/database/event-store or hardware mandates.

## This batch’s verification and safety

Static checks on 2026-09-28 passed: 33 documentation files (6 updated, 27 new), 10 Proposed ADRs, 80 unique catalog/traceability IDs, all D-001–D-022 retained, and 865 resolving repository-relative link/anchor occurrences. Two pinned external links were not fetched. Markdown table/fence and diff-whitespace checks passed. Semantic review covered substitution consent, automatic load-only authority, parallel M2A/M2B, distinct repeated-slot identity, exposure completeness, AI approval date, statuses, security limits and scoring freeze; no application test, build, installation, migration or service startup is run. Link checks validate local targets/anchors, requirement/ADR/milestone consistency and changed-file scope; they do not qualify runtime behavior, external URL availability, scientific outcomes or live production security.

Only this separate documentation worktree/branch is modified and published. Production checkout/branch, database/personal records, configuration, services, deployment, credentials and existing modified debug log remain untouched. No subagents, main merge or PR. Original audit export remains failed; `.codex` permissions were not changed. Stop after publication for owner review.
