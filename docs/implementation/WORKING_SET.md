# Working Set

Last updated: 2026-03-16

## Quick start: run and dogfood (new contributors)

To run the app and verify the Phase 1 path without reading the full architecture:

1. **Start API:** `cd apps/api && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (ensure venv and deps are installed first; see README § Developer Quickstart).
2. **Start web:** `cd apps/web && npm run dev`.
3. **Run validation:** From repo root, `./scripts/mini_validate.sh` (API tests, web tests, web build).
4. **Run the Phase 1 loop:** Follow `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md` — log in, reset to clean Phase 1 (`POST /profile/dev/reset-phase1` or Onboarding → Developer Tools → "Reset Current User to Clean Phase 1"), generate week, open Today, log a set, submit check-in/review, check history, apply adaptation, regenerate week.

For implementation work (e.g. changing coaching logic or UI), use the full read order below and the execution guides.

## Read These First

For any new implementation pass, read in this order:

1. `docs/DOCUMENTATION_STATUS.md`
2. `docs/implementation/WORKING_SET.md`
3. `docs/architecture/GOVERNANCE_CONSTITUTION.md`
4. `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
5. `docs/current_state_decision_runtime_map.md`
6. `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`
7. `docs/implementation/FORBIDDEN_PATTERNS.md`

Only then open supporting docs for the exact decision family or product surface you are changing.

## Law

These docs settle disputes:

- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`

## Current-State Maps

These docs describe branch reality right now:

- `docs/current_state_decision_runtime_map.md`
- `docs/Architecture.md`
- `docs/Master_Plan.md`

Use them to understand what is live, what is still mixed, and what the next pressure points are.

## Execution Guides

These docs tell you how to work the current wave:

- `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`
- `docs/implementation/FORBIDDEN_PATTERNS.md`
- `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md` — Phase 1 path verification; use for dogfooding. REMEDIATION_CHECKLIST is retired; see ACTIVE_REMEDIATION_RAIL § Next Tasks for current work order.

## Supporting / Reference

Open these only when the task needs them:

- `docs/contracts/`
- `docs/testing/`
- `docs/flows/`
- `docs/process/`
- `docs/guides/`
- `docs/plans/` — for Today page UI work see `docs/plans/2026-03-15-today-page-redesign-design.md`
- `docs/redesign/`
- `docs/ui-parity/`
- `docs/validation/`

## Evidence Only

These explain what was observed on a pass. They do not grant new authority:

- `docs/audits/`

## Historical Only

These are preserved for context, not direction:

- `docs/archive/ai-handoffs/`
- `docs/archive/reviews/`
- `docs/archive/historical/`
- `docs/archive/temp/`

The archived `docs/archive/ai-handoffs/AI_CONTINUATION_GOVERNANCE.md` is historical AI guidance only. It is not a peer to the constitution.

## Default Rule

If a doc is not law, current-state, or an active execution guide, do not treat it as permission to add new coaching logic.
