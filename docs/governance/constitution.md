# Constitution, authority and working rules

Date: 2026-09-28. Status: **Owner-approved integration basis, 2026-09-28**. This hierarchy is active for documentation and future work on this review branch. Detailed ADR mechanisms remain Proposed; integration is not release acceptance or main-branch activation. Evidence: [audit](../evidence/README.md#audit-reference-and-migration-plan), [inventory](../evidence/README.md#audit-reference-and-migration-plan), and the existing [decision ledger](../DECISIONS.md).

## Active documentation authority hierarchy

| Order | Authority | Scope and conflict treatment |
|---|---|---|
| 1 | Explicit owner requirements and applicable safety/privacy/licensing constraints | Define desired outcomes and authorized scope; do not infer owner consent. |
| 2 | Product contract and constitution | Governing mode permissions, invariants and documentation authority, approved as this branch's integration basis. |
| 3 | Accepted ADRs + preserved historical decision ledger | Durable choices under the product contract. All ten new ADRs remain Proposed; D-001–D-022 are retained and not silently superseded. |
| 4 | Contracts / requirements | Operationalize approved outcomes; proposed mechanisms are labeled. Catalog and traceability connect predicates to evidence. |
| 5 | Architecture | Desired ownership is distinct from revision-scoped current-state observations. Neither changes product permissions. |
| 6 | Roadmap / bounded plans | Sequence separately authorized work; Proposed plans do not authorize implementation. |
| 7 | Tests / evidence | Scope observations by revision/environment; passing tests cannot override requirements. |
| 8 | Historical / supporting / archive | Preserve original rationale, unfinished work, provenance and dated observations without competing current authority. |

The central index owns navigation and status, not duplicate normative prose. Role names identify responsibilities; one person may hold several. Keep check execution, review and product acceptance separately recorded.

Authored source prescriptions are domain authority under the Authored contract, subject to explicit safety/conflict outcomes. Executable `docs/rules/**` are runtime assets, not ordinary prose to reorganize. Compiled knowledge remains build-owned. Documentation location does not by itself determine authority.

## Runtime boundaries carried forward

- Authored Full Body Phase 1 and Phase 2 remain separate from generated programs; generated paths cannot mutate or reinterpret authored templates.
- Raw onboarding answers become deterministic `GenerationProfile` before generation decisions consume them.
- Explicit owner approval on 2026-09-28: core workout/program decisions remain deterministic and auditable; AI/LLMs may explain, converse, research, summarize, analyze and assist development, but never directly determine runtime training prescriptions. Explanations cannot acquire mutation authority. This is current approval, not retroactive acceptance of D-005 or detailed ADR-004 mechanisms.
- `manual`/`auto` selection is separate from explicit Customized consent. An equipment/safety/pain exception is scoped to its source slot. Any source-approved substitution requires explicit user confirmation and preserves source-slot/performed-variant identity. Normal automatic Authored adaptation is working load, with reason/evidence and override.
- Preserve existing decision modules and compatibility boundaries until a reviewed change names their replacement and consequences.
- Metadata-v2 scoring activation remains frozen; accounting improvements are not implicit scoring approval.

No application-wide event-sourcing rewrite is mandated. Evaluate the smallest design that provides reliable occurrence identity, retry safety, correction/undo and reconstruction. Immutable evidence and explicit supersession are documentation requirements, not a prescribed database architecture.

## Concordance with the existing decision ledger

Retain original IDs and the ledger's existing 2026-03-20 date context. The ledger contains **D-001 through D-022**. The audit's shorter D-001–D-020 preservation reference must not omit D-021 or D-022. This integration records concordance and labels the ledger role; it preserves the original ledger body, does not mint accepted ADRs or invent new dates for old decisions.

| Existing identifiers | Retained meaning and proposed interpretation |
|---|---|
| D-001–D-004 | Preserve canonical/reference separation, diagnostic guide ownership, exclusion of raw reference documents from runtime, and compiled artifacts. |
| D-005 | Preserve the historical deterministic/no-paid-LLM statement. The owner explicitly approved the stronger prescription boundary on 2026-09-28; [ADR-004](../adr/0004-deterministic-runtime-and-ai-boundary.md) records that date and separates proposed mechanisms. |
| D-006–D-007 | Preserve first-class authored programs and explicit authored/generated mode separation. Proposed product terminology and consent must be mapped explicitly to existing keys. |
| D-008–D-010 | Keep doctrine, policy and engine distinct; hard constraints govern soft preferences. |
| D-011 | Preserve minimum-viable fallback intent within current consent/safety boundaries: disclose reductions/infeasibility; never unlock hidden authored mutation or unsafe execution. |
| D-012–D-013 | Retain bounded adaptation and data-sufficiency checks, with an explicit safety exception. |
| D-014–D-015 | Retain generated v1 Full Body scope; Upper/Lower, PPL and best-split selection remain future work until accepted. |
| D-016 | Preserve the historical milestone's no-router/database/authored/generated behavior-change constraint. It is not a perpetual ban on later separately authorized milestones; this pass is independently docs-only. |
| D-017–D-018 | Preserve declared temporary onboarding seeds and local/offline compilation goals without elevating seeds into permanent doctrine. |
| D-019–D-020 | Generated programs are original designs; temporary compatibility defaults are named, traced and nonauthoritative. |
| D-021–D-022 | Preserve anti-copy topology boundaries; source program IDs can support exercise provenance/ranking, never target layout reconstruction. |

Conflicts requiring different behavior need a proposed ADR naming the original decision, alternatives, compatibility and explicit supersession. Do not silently relabel a locked decision or historical milestone as accepted new architecture.

## Change and acceptance process

1. Identify the controlling owner requirement, existing decision and affected contract. Record the discrepancy using revision-scoped evidence.
2. Propose the smallest bounded amendment; include alternatives, failure behavior, compatibility, migration and verification needs. Mark proposed technical decisions separately from owner requirements.
3. Obtain the appropriate decision/implementation authorization. Approval to continue drafting or integrate docs is not approval to modify runtime or deploy.
4. Implement only the authorized scope, preserving source provenance and evidence. For sensitive generated/onboarding/progression/routing changes, update meaningful behavior tests and deterministic traces where appropriate.
5. Record implementation revision, qualification environment and procedure, raw result/artifact, limitations, reviewer and separate owner acceptance. Retain failed results and add corrective evidence.

A milestone is not complete because a plan exists, tests happen to pass, or an old document says complete. Changes to an accepted baseline require explicit supersession and updated consumers, not replacement of unfavorable evidence.

## Contributor and AI working rules

Before sensitive work, follow [AGENTS.md](../../AGENTS.md) and the [scoped context manifest](../context/CONTEXT_MANIFEST.yaml). Read the product contract/constitution, relevant ADR (including its Proposed status), area contract, runtime authority, requirements and registered plan in that order. Read historical material only when an active reference makes it relevant. There is no blanket requirement to read every historical doctrine/index.

Use the completed audit as starting evidence. Read additional source only for a specific contract/planning question; record unresolved issues instead of broadening the audit. Classify existing failures individually as confirmed implementation defect, obsolete/conflicting expectation, fixture/environment issue, or unresolved. Replace obsolete checks with protections grounded in the controlling contract; never restore authored mutation or weaken intended protection merely to obtain green results.

Use explicit disposable verification environments for any later authorized tests. Do not trust database defaults, inherited Compose settings or SQLite results as proof of PostgreSQL concurrency/migration safety. No qualifying run is authorized by these drafts. Protect credentials and personal data; evidence must not retain reset tokens, passwords or sensitive URLs.

For this architecture pass, modify documentation only in the separate review worktree on `docs/planning-baseline-2026-09-28`; the owner authorizes a documentation commit and branch publication. Never modify the production checkout/branch, runtime code/rules/artifacts, database, personal records, live configuration, credentials, private keys, logs, services or deployment. Do not run application tests/builds/installations/startup/migrations, merge into main or create a PR. Leave the debug log, abandoned WSL rebase and `.codex` permissions untouched. Use no subagents. Stop after publishing this batch for owner review.

## Integration ownership

The [documentation index](../README.md) and [complete migration registry](../audits/2026-09-28-documentation-migration-registry.md) establish active navigation and explicit historical roles on this branch. The [migration report](../audits/2026-09-28-documentation-authority-migration.md) records paths, compatibility exceptions and static qualification. The product owner accepts permissions/outcomes; technical/security maintainers review mechanisms; the operator owns separately authorized deployment/recovery evidence.

Preserve the path-scoped authority and truth-budget principles carried from the old governance: name the family owner, applicable path, actual inputs/outcomes and limits before claiming sovereignty; do not infer repository-wide ownership from one qualified path. Presentation may render owned explanation facts; it must not invent causes from rule-code names. Compatibility façades and executors must not introduce shadow doctrine. Behavioral verification must exercise outcomes and must-fail boundaries, not only narrative strings. Proposed replacement modules are not an instruction to remove compatibility wrappers now.

The [ADR concordance](../adr/README.md#historical-concordance) retains D-001–D-022 and unresolved interpretations. Old authority claims remain in historical bodies behind explicit notices; they no longer compete with this hierarchy. No Proposed ADR overrides a historical decision. Main-branch integration and every runtime implementation/release remain separately authorized.
