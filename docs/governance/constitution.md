# Constitution, authority and working rules

Date: 2026-09-28. Status: **Proposed; not integrated or owner-accepted**. This is a reviewable hierarchy, not a claim that current repository authority has already changed. Evidence: [audit](../../../Hypertrophy-Audit-2026-09-28.md), [inventory](../../../Documentation-Migration-Inventory.md), and the existing [decision ledger](/home/rocco/hypertrophyapp/docs/DECISIONS.md).

## Proposed authority hierarchy

| Order | Authority | Scope and conflict treatment |
|---|---|---|
| 1 | Explicit owner requirements and applicable safety, privacy and licensing constraints | State intended user outcomes and boundaries. New technical proposals cannot manufacture owner consent. Record a conflict that cannot be satisfied. |
| 2 | Accepted product contract and constitution | Define mode permissions, invariants and change control. Amend explicitly; do not infer new permissions from current code. |
| 3 | Accepted ADRs and retained decision ledger | Durable technical choices within the product contract; changes require a named successor and compatibility analysis. |
| 4 | Accepted domain, runtime-authority and high-risk contracts | Define identities, units, inputs, outputs, failure behavior and component ownership under those decisions. |
| 5 | Requirements catalog and traceability | Translate governing outcomes into testable predicates; link evidence, dependencies and gates. |
| 6 | Architecture descriptions and operations/quality procedures | Describe implementations and safe qualification. Current-state documents are descriptive and revision-scoped. |
| 7 | Roadmap and bounded plans | Sequence authorized work and tests. A proposed plan confers no execution or deployment authority. |
| 8 | Audits, evidence, research, generated guides and archives | Preserve observations, provenance and history. Passing tests and old checkmarks do not override a requirement. |

The central index owns navigation and status, not duplicate normative prose. Role names identify responsibilities; one person may hold several. Keep check execution, review and product acceptance separately recorded.

Authored source prescriptions are domain authority under the Authored contract, subject to explicit safety/conflict outcomes. Executable `docs/rules/**` are runtime assets, not ordinary prose to reorganize. Compiled knowledge remains build-owned. Documentation location does not by itself determine authority.

## Runtime boundaries carried forward

- Authored Full Body Phase 1 and Phase 2 remain separate from generated programs; generated paths cannot mutate or reinterpret authored templates.
- Raw onboarding answers become deterministic `GenerationProfile` before generation decisions consume them.
- No runtime LLM inference decides planning. Deterministic decisions disclose qualified inputs, rule/artifact versions and reasons where appropriate.
- `manual`/`auto` selection is separate from explicit Customized consent. An equipment/safety exception is scoped to the affected source slot.
- Preserve existing decision modules and compatibility boundaries until a reviewed change names their replacement and consequences.
- Metadata-v2 scoring activation remains frozen; accounting improvements are not implicit scoring approval.

No application-wide event-sourcing rewrite is mandated. Evaluate the smallest design that provides reliable occurrence identity, retry safety, correction/undo and reconstruction. Immutable evidence and explicit supersession are documentation requirements, not a prescribed database architecture.

## Concordance with the existing decision ledger

Retain original IDs and the ledger's existing 2026-03-20 date context. The ledger contains **D-001 through D-022**. The audit's shorter D-001–D-020 preservation reference must not omit D-021 or D-022. This draft records concordance; it does not rewrite the ledger, mint accepted ADRs or invent new dates for old decisions.

| Existing identifiers | Retained meaning and proposed interpretation |
|---|---|
| D-001–D-004 | Preserve canonical/reference separation, diagnostic guide ownership, exclusion of raw reference documents from runtime, and compiled artifacts. |
| D-005 | Preserve deterministic runtime/no paid-LLM dependency; the owner's current no-runtime-LLM requirement is stronger and applies to all runtime planning inference. |
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

Before future sensitive runtime changes, read every document listed in the existing [context manifest](/home/rocco/hypertrophyapp/docs/context/CONTEXT_MANIFEST.yaml), including the constitution, runtime map, generated doctrine, metadata model, remediation roadmap, onboarding/profile/strategy specifications, roadmap, AI rules and documentation status required by [AGENTS.md](/home/rocco/hypertrophyapp/AGENTS.md). Update the manifest and instruction references together only during separately approved integration. This draft does not replace that mandatory reading contract.

Use the completed audit as starting evidence. Read additional source only for a specific contract/planning question; record unresolved issues instead of broadening the audit. Classify existing failures individually as confirmed implementation defect, obsolete/conflicting expectation, fixture/environment issue, or unresolved. Replace obsolete checks with protections grounded in the controlling contract; never restore authored mutation or weaken intended protection merely to obtain green results.

Use explicit disposable verification environments for any later authorized tests. Do not trust database defaults, inherited Compose settings or SQLite results as proof of PostgreSQL concurrency/migration safety. No qualifying run is authorized by these drafts. Protect credentials and personal data; evidence must not retain reset tokens, passwords or sensitive URLs.

For this pass, create draft docs only in the separate output directory. Do not modify the checkout, rules, artifacts, database, personal records, live config, credentials, private keys, logs, services or deployment. Do not run production tests/builds/installations/startup/migrations or mutate Git. Leave the debug log, abandoned WSL rebase and `.codex` permissions untouched. Do not use subagents. Stop after this first batch and report unresolved decisions; continuation needs approval.

## Integration ownership

The maintainer proposes successors using the complete 199-file inventory, preserving decisions, negative findings, licensing and unresolved task disposition. Check real path consumers before relocation. The product owner accepts permissions and outcomes; technical/security maintainers review mechanisms; the operator owns deployment and recovery evidence. Indexes, authority labels, context references and successor notices change coherently. No competing hierarchy is made active merely by copying these drafts into the repository.
