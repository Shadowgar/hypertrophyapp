# Current Milestone Plan: Runtime Quality Stabilization and Documentation Alignment

Last updated: 2026-05-10

This is the active implementation authority. If it conflicts with broader roadmap material, this document wins for current coding order.

Status: active on 2026-05-10.

## Milestone Intent

Initial generated full-body runtime integration is complete. The active milestone is now reality alignment plus quality lock hardening, with deterministic behavior and authored/generated separation preserved.

## Shipped

- Generated Full Body runtime is integrated into live `/plan/generate-week` with compatibility-preserving identity and deterministic fallback behavior.
- Generated runtime is deterministic and non-LLM at runtime.
- Generated constructor/runtime quality improvements landed across skeleton, volume floor behavior, distribution controls, and consistency checks.
- Authored day-count adaptation includes dose-preserving redistribution for selected days `< 5`.
- Authored 5-day passthrough preserves source dose.
- Authored exercise prescriptions remain unchanged.
- Metadata-v2 scoring remains frozen/no-op.

## Active

1. Documentation truth alignment across current-state and milestone docs.
2. Generated quality lock hardening and regression-proofing:
   - weekly volume distribution balance
   - role/skeleton durability under expansion
   - core reporting and exposure consistency
   - today/latest-week/session summary consistency
3. Authored redistribution validation across Phase 1/2 with live/browser verification.

## Blocked / Not Yet Closed

- Full authored doctrine certification is not closed until complete source-vs-app parity reporting is finalized.
- Safety/ops hardening is partial; technical guardrails for destructive DB workflows need stronger enforcement.

## Deferred

- runtime integration beyond generated `Full Body`
- `Upper/Lower` and `PPL` generated runtime integration
- mesocycle redesign
- specialization overlays
- adaptation ledger
- runtime LLM usage
- DB schema/migration redesign for this wave

## Scope (Current Milestone)

- documentation sync and authority cleanup
- generated runtime quality stabilization work
- authored adaptation regression protection and validation
- deterministic trace and contract consistency checks

## Hard Boundaries

- no generated/authored path conflation
- no authored prescription mutation
- no metadata-v2 scoring re-enable
- no runtime LLM
- no weaken of regenerate/progress guards

## Acceptance Criteria

- documentation accurately reflects shipped runtime behavior
- generated quality lock regression categories are defined and executable
- authored redistribution behavior is validated for 2/3/4/5-day configurations
- generated/authored path separation remains intact
- metadata-v2 scoring remains frozen/no-op

## Verification Categories

- generated runtime integration and distribution tests
- authored adaptation and continuity tests
- latest-week/today/progress consistency checks
- non-regression checks for catalog selection and route contracts

## Notes

- This milestone replaces the older “Generated Full Body Runtime Integration” implementation plan as the active execution authority.
- Runtime integration work is now considered shipped baseline, not active future scope.
