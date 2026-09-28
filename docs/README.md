# Documentation authority and navigation

The documentation authority baseline was owner-approved on **2026-09-28**. This is the repository's single documentation entry point and controlling hierarchy. Product requirements, Proposed technical mechanisms, implementation, revision-scoped verification and release acceptance remain distinct. Audited application revision: `df9965232ce731f8234d222acc526a90bc6be620`; documentation migration history is retained in the audit records linked below.

## Controlling hierarchy

Owner requirements → **[product contract](requirements/product-contract.md) / [constitution](governance/constitution.md)** → Accepted ADRs + [preserved historical decision ledger](DECISIONS.md) → contracts / requirements → architecture → roadmap / bounded plans → tests / evidence → historical / supporting / archive.

Owner-approved product directions govern desired behavior. All ten [ADRs](adr/README.md) remain **Proposed**; a Proposed ADR cannot supersede D-001–D-022. ADR-004's deterministic prescription principle is owner-approved on 2026-09-28; its detailed enforcement remains Proposed. Current-state observations and runtime defects cannot amend the product contract.

| Area | Entry point and role |
|---|---|
| Product / governance | [Product](requirements/product-contract.md), [constitution](governance/constitution.md), [AI working rules](governance/ai-working-rules.md), [working agreements](governance/working-agreements.md), [source provenance](governance/source-provenance.md). |
| Decisions | [ADR lifecycle, ten records and D-001–D-022 concordance](adr/README.md). |
| Requirements | [80-ID catalog](requirements/catalog.md) and [traceability](requirements/traceability.md); partial implementation is distinguished from missing full qualification. |
| Architecture | [Target system](architecture/system.md), [audited current state](architecture/current-state.md), [domain](architecture/domain-model.md), [data](architecture/data-model.md), [runtime authority](architecture/runtime-authority.md), [exercise catalog](architecture/exercise-catalog.md). |
| High-risk contracts | [Contract map](contracts/README.md): source/execution, normalized onboarding, Customized generation, load/exposure, selected dates, recommendations and metadata accounting. |
| Roadmap / plans | One [milestone roadmap](roadmap/milestones.md); [bounded plan registry and statuses](plans/README.md). M2A load and M2B actual dates are parallel after relevant M0/M1 foundations. |
| Security | [Security architecture](security/architecture.md), [threat model](security/threat-model.md), [urgent recovery brief](security/urgent-account-recovery.md), [Proposed recovery plan](plans/urgent-account-recovery.md). [Disclosure policy](../SECURITY.md) and [database safety lock](../DB_SAFETY_LOCK.md) remain applicable. |
| Quality | [Test strategy](quality/test-strategy.md), [release gates](quality/release-gates.md), [Authored qualification](quality/authored-qualification.md), [manual qualification](quality/manual-qualification.md), [issue template](problems/issue-template.md). |
| User flow / development | [Desired flows](ux/flows.md), [safe development context](operations/development.md), [agent instructions](../AGENTS.md) and [scoped context manifest](context/CONTEXT_MANIFEST.yaml). |
| Audit / evidence | [Evidence/provenance registry](evidence/README.md), [sanitized September audit](audits/2026-09-28-codebase-product-documentation-audit.md), [199-file disposition registry](audits/2026-09-28-documentation-migration-registry.md), [migration report](audits/2026-09-28-documentation-authority-migration.md). |
| Historical material | [Archive navigation](archive/README.md), [legacy evidence](evidence/legacy/README.md), [retained unfinished tasks](audits/2026-09-28-legacy-task-register.md). Old root/architecture/implementation indexes and plans are historical/supporting despite original active/master claims below their notices. |
| Generated reference / runtime assets | [Generated guides notice](guides/generated/README.md) and [source provenance](governance/source-provenance.md). Executable [docs/rules](rules) is a compatibility/runtime asset boundary, outside prose migration. |

## Status vocabulary

| Status | Meaning |
|---|---|
| Owner-approved desired requirement/direction | Owner accepted the intended product outcome; mechanism, implementation and release evidence remain separate. |
| Proposed technical mechanism | Design awaiting appropriate review; grants no implementation/deployment authority. |
| Accepted ADR | A record with explicit approver, date and scope. All ten current ADRs remain Proposed. |
| Implemented | Code or documentation exists for the stated scope and revision; not automatically verified. |
| Verified for revision/environment | Named procedure and evidence support stated criteria within recorded limits. |
| Owner-accepted release/milestone | Explicit owner acceptance of a particular release scope and evidence. Documentation approval alone does not accept an M0–M6 release. |
| Superseded | Original authority replaced by a named current successor. Ledger decisions require an actually Accepted superseding ADR; notices on old indexes do not revoke them. |
| Historical/supporting | Original observations, designs, rationale or evidence retained at their original date/revision/environment. No current implementation permission. |

Plan lifecycle is defined once in the [plan registry](plans/README.md). Drafting/integration approval does not approve the urgent recovery plan for implementation.

## Compatibility and evidence boundaries

All 199 audited files have an explicit disposition, retained path, original SHA-256 and current role in the registry. Original bodies, negative findings and unfinished work are retained; some old paths remain compatibility notices. Historical Markdown is interpreted under its notice, not its old internal authority claims. Legacy evidence and generator-owned reports remain scoped to their original context; missing revision/environment remains unknown.

`docs/rules/**`, generated training knowledge, generated guide artifacts, source materials, asset catalog and provenance index are protected runtime/source/build assets. Generated guides are reference/build products, not runtime prescription authority. Rule relocation requires separately authorized application migration and tests. Tool-consumed Master Plan and validation report paths stay in place; tooling migration remains a separately scoped implementation task.

Active references resolve inside the repository without owner-machine or private audit-state paths. The complete raw audit package originally lived outside Git and remains there; the repository retains a sanitized summary and all-file disposition registry, not private raw output or proprietary sources. Historical unavailable links are explicitly accounted for in the migration report.

SnakeTracker's pinned [documentation index](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/README.md) and [decision-freeze process](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/adr/0028-architecture-governance-and-decision-freeze.md) remain quality/process references studied in the audit. Their application architecture is not adopted.
