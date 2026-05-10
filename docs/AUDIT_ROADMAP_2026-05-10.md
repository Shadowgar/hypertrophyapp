# Audit Roadmap - 2026-05-10

## Purpose

This document captures post-audit execution priorities after reality alignment identified documentation and runtime-quality governance drift.

## Shipped State Summary

- Generated Full Body runtime is integrated in live `/plan/generate-week`.
- Generated runtime remains deterministic and non-LLM.
- Generated quality work has progressed on skeleton, volume floors, distribution controls, and consistency checks.
- Authored path now supports dose-preserving redistribution for selected days `< 5`.
- Authored 5-day passthrough preserves source dose.
- Authored source prescriptions remain unchanged.
- Generated and authored paths remain separated.
- Metadata-v2 scoring remains frozen/no-op.

## Priority Gaps

1. Documentation drift between March-era milestone docs and current runtime behavior.
2. Generated distribution quality still needs tighter stage ownership and regression locking.
3. Full authored doctrine certification not closed without complete source-vs-app parity report.
4. Safety/ops guardrails for destructive DB workflows need stronger technical enforcement.
5. Product readiness gate needs explicit deterministic verification categories and evidence outputs.

## Phase A - Documentation Sync

Goal:

- align active authority docs with actual runtime state
- clearly distinguish shipped vs active vs deferred work

Deliverables:

- updated `docs/CURRENT_STATE.md`
- updated `docs/ROADMAP.md`
- updated `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`
- updated `docs/NEXT_ACTIONS.md`
- updated `docs/DOCUMENTATION_STATUS.md`

## Phase B - Generated Quality Lock

Goal:

- regression-proof generated normal full-body distribution quality while keeping deterministic runtime behavior

Focus areas:

- weekly-volume-first distribution architecture
- role/skeleton durability under density expansion
- caps/floors ordering and anti-dominance controls
- core visibility and weekly mapping consistency
- latest-week/today/workout summary consistency

Recommended command/test categories:

- `apps/api/tests/test_generated_full_body_template_constructor.py`
- `apps/api/tests/test_generated_full_body_runtime_integration.py`
- targeted live validation probes for generated normal 3-day profiles

## Phase C - Authored Doctrine Certification

Goal:

- certify authored implementation against official source doctrine and adaptation policy

Focus areas:

- full source-vs-app parity matrix
- Week 5 semi-deload parity
- 2/3/4/5-day adaptation behavior validation
- source-dose preservation plus coherence checks

Recommended command/test categories:

- `apps/api/tests/test_authored_generated_path_regression.py`
- `apps/api/tests/test_phase1_canonical_path_smoke.py`
- targeted browser/live authored validations across Phase 1 and Phase 2

## Phase D - Safety/Ops Guardrails

Goal:

- prevent accidental destructive DB actions in live-like environments

Focus areas:

- environment gating for destructive test helpers
- explicit reset safeguards and refusal conditions
- pre-run safety checks in test/probe workflows

Recommended validation categories:

- destructive-path guard behavior tests
- environment marker and refusal-path checks

## Phase E - Product Readiness Gate

Goal:

- establish deterministic go/no-go criteria with repeatable evidence capture

Focus areas:

- onboarding -> generate -> today -> log -> review -> next-week continuity
- generated/authored contract integrity
- route-level consistency and summary integrity

Recommended command/test categories:

- API regression categories for plan/workout/profile/history
- core-engine generation non-regression categories
- release scorecard artifact generation under `docs/validation/`

## Notes

- This roadmap defines execution categories and sequencing only.
- It does not claim completion results for any pending phase.
