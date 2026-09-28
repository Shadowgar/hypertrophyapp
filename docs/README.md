# Documentation and planning draft

Date: 2026-09-28. Package status: **Proposed; review pending; not integrated**. These documents are a first review batch, not an accepted replacement for repository governance or authorization to implement a plan.

Audited source: `df9965232ce731f8234d222acc526a90bc6be620`. The checkout still matched that revision when this package was prepared. Git status contained only the pre-existing modified `logs/app-debug.log`, which was left alone. Implementation descriptions refer to the audited source, not a verified deployed image.

## Read this package

| Document | Purpose and proposed owner role |
|---|---|
| [Product contract](requirements/product-contract.md) | Owner-stated mode permissions and user outcomes; product owner. |
| [Constitution and working rules](governance/constitution.md) | Proposed authority hierarchy, decision concordance, contributor rules and change control; product owner and maintainer. |
| [Milestone roadmap](roadmap/milestones.md) | Proposed sequence, independent M0 packages, dependencies and acceptance gates; product owner. |
| [Urgent account-recovery brief](security/urgent-account-recovery.md) | Established source findings, unknown production conditions and containment choices; security maintainer and operator. |
| [Urgent account-recovery implementation plan](plans/urgent-account-recovery.md) | Bounded changes, compatibility, tests, deployment prerequisites and stop conditions; implementing maintainer and operator. |

These six files mirror intended repository-relative paths. Working rules are consolidated in the constitution for this batch. No remaining documentation has been generated.

## Status and evidence

Keep these states separate: **Proposed**, **Accepted requirement**, **Implemented**, **Verified for a revision/environment**, and **Owner-accepted**. A document can describe an owner-stated requirement while its proposed architecture remains unaccepted. Implementation and test results do not imply product acceptance. Record supersession explicitly; preserve original dated evidence and failures.

The starting evidence is the [audit](../../Hypertrophy-Audit-2026-09-28.md), [199-file migration inventory](../../Documentation-Migration-Inventory.md), [machine-readable inventory](../../document-inventory.json), and [verification notes](../../Verification-Notes.md). The notes govern interpretation of isolated runs and their limitations. The managed security export remains **failed** because its directory-privacy check rejected pre-existing permissions. Independent source findings are retained; there is no sealed managed result or complete dependency, ingress or production-security certification.

No broad audit was repeated. Additional source reads were limited to recovery/authentication, mail transport, validation logging, their existing tests and UI/configuration consumers, plus the decision ledger, to resolve specific planning questions. No live recovery requests or production configuration/session inspection occurred.

## Continuation and integration

The [roadmap](roadmap/milestones.md) identifies later deliverables. Full architecture/domain documents, high-risk contracts, requirements catalog and traceability, ADRs, evidence/test policy, operations runbooks and the staged migration plan remain deferred pending approval to continue. Future paths mentioned in this batch are destinations, not existing authorities.

Before a separately approved documentation integration, reconcile all 199 inventory rows, retain original decisions and unresolved tasks, and check path consumers in code, tests, workflows, packaging and AI instructions. Create successor notices and update indexes and the context manifest together. Keep executable `docs/rules/**` paths and contents intact; preserve generated-guide ownership, source provenance and licensing. No existing document was moved, archived or edited here.

Documentation approval, implementation authorization, and deployment authorization are separate actions. The immediate security packages can be reviewed independently of the full documentation migration and training-history redesign.

## Quality reference and checks

Use the pinned SnakeTracker [documentation index](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/README.md), [decision-freeze record](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/adr/0028-architecture-governance-and-decision-freeze.md), and [milestone roadmap](https://github.com/Shadowgar/SnakeTracker/blob/87652f8ea80f6328a15385dc2cc32beaf4dbc9e2/docs/roadmap/milestones.md) as process references already studied in the audit. Borrow explicit authority, supersession and criterion-linked evidence. No architecture, event-sourcing model, database choice or hardware target is adopted from that project, and its implementation is not independently certified here.

Static package verification completed on 2026-09-28: exactly six Markdown files; all 45 local link occurrences resolve; no missing targets. Three pinned external reference links were retained without fetching them again. Status labels, M0 package identifiers, SEC-S1/S2 boundaries, D-001–D-022 concordance and quoted baseline results were checked for consistency across the batch. Absolute source links refer to the current checkout and can drift later; use the recorded revision when interpreting them. No application test, build, installation or migration was run. These checks establish documentation consistency/navigation, not application behavior, external URL availability, deployment conditions or owner acceptance.

## Production boundaries

The production checkout stayed read-only. Database contents, personal training records, logs, credentials, private keys and live environment files were not read or copied into this package. No database mutation, tests/builds/installations, migration, service startup/restart, deployment or Git mutation was performed. The abandoned WSL rebase and `.codex` permissions were untouched. Draft creation occurred only under this separate output directory.
