# Documentation Status

Last updated: 2026-03-12

Purpose: this is the canonical documentation index. Use it to determine what is authoritative, what is supporting, and what is archived.

## Read First

1. `docs/DOCUMENTATION_STATUS.md`
2. `docs/architecture/GOVERNANCE_CONSTITUTION.md`
3. `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
4. `docs/current_state_decision_runtime_map.md`
5. `docs/Architecture.md`
6. `docs/Master_Plan.md`

## Authoritative Docs

These are the only documents that should settle architectural authority disputes.

- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
  Constitutional authority for sovereignty, trust, traces, and architectural law.
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
  Permanent ownership map for runtime authority.
- `docs/current_state_decision_runtime_map.md`
  Operational current-state ownership map for the branch reality.
- `docs/Architecture.md`
  Active runtime architecture and boundary description.
- `docs/Master_Plan.md`
  Project direction and execution order.

## Top-Level Daily Drivers

Top-level `docs/` is intentionally limited to:

- `docs/DOCUMENTATION_STATUS.md`
- `docs/Master_Plan.md`
- `docs/Architecture.md`
- `docs/current_state_decision_runtime_map.md`

Everything else should live in a supporting folder or archive.

## Supporting Docs

These are active references, but they are subordinate to the authoritative set above.

- `docs/architecture/`
  Supporting architecture references, milestones, remediation checklists, and trust-model material.
- `docs/contracts/`
  Active schema and contract docs:
  `Canonical_Program_Schema.md`, `High_Risk_Contracts.md`, `Offline_Sync_Deterministic_Contract.md`
- `docs/audits/`
  Audit evidence and review snapshots used to evaluate branch reality.
- `docs/validation/`
  Validation evidence and generated reports.
- `docs/testing/`
  Testing runbooks and internal tester guidance.
- `docs/flows/`
  Product-flow and onboarding flow references.
- `docs/process/`
  Contributor/process references such as working agreements.
- `docs/ui-parity/`
  UI parity checklists and capture folders.
- `docs/plans/`
  Implementation plans and execution-wave planning artifacts.
- `docs/redesign/`
  Legacy redesign/reference material that still informs current structure but is not day-to-day authority.
- `docs/guides/`
  Build-time extraction and provenance artifacts only. Not runtime coaching authority.

## Archived Docs

These are preserved for history, AI handoff context, or review evidence. They are not authoritative.

- `docs/archive/ai-handoffs/`
  Archived AI prompts, handoffs, runbooks, backlogs, and temporary governance scaffolding.
  `AI_CONTINUATION_GOVERNANCE.md` is archived here and explicitly demoted; constitutional governance now lives in `docs/architecture/GOVERNANCE_CONSTITUTION.md`.
- `docs/archive/reviews/`
  Historical review snapshots and draft review material.
- `docs/archive/historical/`
  Historical stubs and deferred-reference documents.
- `docs/archive/temp/`
  Temporary output artifacts retained only as historical evidence.

## Structure Rules

- Do not create new top-level docs unless they belong in the daily-driver set.
- If a document governs architecture, prefer updating an existing authoritative doc instead of creating a peer.
- If a doc is AI-operational, dated, temporary, or handoff-specific, archive it instead of keeping it at the top level.
- If a doc becomes stale but still contains useful evidence, move it to archive rather than deleting it.

## Quick Classification Guide

- Architectural law: `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- Runtime ownership: `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
- Current branch ownership reality: `docs/current_state_decision_runtime_map.md`
- System architecture: `docs/Architecture.md`
- Project direction: `docs/Master_Plan.md`
- Contracts and schemas: `docs/contracts/`
- Audits and evidence: `docs/audits/`, `docs/validation/`
- Historical or AI-operational context: `docs/archive/`
