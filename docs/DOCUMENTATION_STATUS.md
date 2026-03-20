# Documentation Status

Last updated: 2026-03-20

Purpose: this is the canonical documentation index for implementation work. Use it to determine reading order, authority hierarchy, and where a document belongs before adding or moving anything.

## Read Order For Future AI Work

1. `docs/DOCUMENTATION_STATUS.md`
2. `docs/implementation/WORKING_SET.md`
3. `docs/architecture/GOVERNANCE_CONSTITUTION.md`
4. `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
5. `docs/current_state_decision_runtime_map.md`
6. `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`
7. `docs/implementation/FORBIDDEN_PATTERNS.md`
8. Only then read the exact supporting docs needed for the task

## Authority Hierarchy

1. `docs/architecture/GOVERNANCE_CONSTITUTION.md`
   This is the top governing document. If another doc conflicts with it, the constitution wins.
2. `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
   This defines the permanent runtime-role model under the constitution.
3. `docs/current_state_decision_runtime_map.md`
   This is the current branch-reality map. It does not override the constitution, but it does override stale plans or handoffs.
4. `docs/implementation/`
   These are active execution rails. They guide current work but do not create new architectural law.
5. All supporting, audit, and archive material
   Useful context only. Never treat it as governing authority.

Relationship note:

- `docs/archive/ai-handoffs/AI_CONTINUATION_GOVERNANCE.md` is archived historical AI guidance only.
- It is not a peer to `docs/architecture/GOVERNANCE_CONSTITUTION.md`.
- If a future AI-operational doc is added, it must either live under `docs/implementation/` as a non-governing execution guide or under `docs/archive/ai-handoffs/` as historical context.

## Authoritative

These settle architectural disputes:

- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`

## Operational Current-State

These describe the live branch and current product/runtime direction:

- `docs/current_state_decision_runtime_map.md`
- `docs/Architecture.md`
- `docs/Master_Plan.md`
- `docs/architecture/ARCHITECTURE_INDEX.md`
- `docs/architecture/REMEDIATION_CHECKLIST.md`
- `docs/architecture/TRUST_AND_MATURITY_MODEL.md`
- `docs/architecture/GOLD_PATH_MILESTONE.md`

## Active Implementation

These are the execution rails for current coding passes:

- `docs/implementation/WORKING_SET.md`
- `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`
- `docs/implementation/FORBIDDEN_PATTERNS.md`
- `docs/implementation/phase2_fullbody_intent_contract.md`

## Supporting / Reference

These help implementation but do not grant authority on their own:

- `docs/contracts/`
- `docs/testing/`
- `docs/flows/`
- `docs/process/`
- `docs/guides/`
- `docs/plans/` — includes **Today page redesign** design and implementation records (`docs/plans/2026-03-15-today-page-redesign-design.md`, `docs/plans/2026-03-15-today-page-redesign-implementation.md`)
- `docs/redesign/`
- `docs/ui-parity/`
- `docs/rules/`

## Audit / Evidence

These record what was observed or validated on a pass:

- `docs/audits/`
- `docs/validation/`
- Phase 2 validation artifacts:
  - `docs/validation/phase2_fullbody_parity_matrix.md`
  - `docs/validation/phase2_fullbody_handoff.md`

Use them as evidence, not as execution instructions.

## Historical / Archive

These are preserved for context only:

- `docs/archive/ai-handoffs/`
- `docs/archive/reviews/`
- `docs/archive/historical/`
- `docs/archive/temp/`

Do not read archive first during active implementation unless a current-state or active-implementation doc explicitly sends you there.

## Top-Level `docs/` Rule

Top-level `docs/` should stay small and high-signal:

- `docs/DOCUMENTATION_STATUS.md`
- `docs/Architecture.md`
- `docs/Master_Plan.md`
- `docs/current_state_decision_runtime_map.md`

Active execution rails belong under `docs/implementation/`.
Historical AI handoffs and temporary review artifacts belong under `docs/archive/`.

## Placement Rules

- New governing law belongs in an existing authoritative doc unless a genuinely new constitutional document is required.
- New current-wave implementation guidance belongs in `docs/implementation/`.
- Dated evidence belongs in `docs/audits/` or `docs/validation/`.
- AI prompts, passoff notes, and temporary runbooks belong in `docs/archive/ai-handoffs/` unless they are actively maintained execution rails.
- If a document is no longer active but still useful, archive it rather than deleting it.
