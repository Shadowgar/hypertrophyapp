# Schema Validation — Implementation Plan

**Date:** 2026-03-16  
**Design:** [2026-03-16-schema-validation-design.md](2026-03-16-schema-validation-design.md)

## Tasks

1. **Add validator helpers for program template** — In `apps/api` or `packages/core-engine`, add a small module that loads program JSON and checks required fields and structure (phases/weeks/days/slots, unique ids, exercise_id presence). Emit a list of diagnostics (path, code, message). Reuse or align with [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md) and existing Pydantic models where possible.
2. **Add validator for onboarding package** — Same style; validate `program_id` alignment, week-sequence to week-template mapping, day/slot uniqueness. Reference loader and onboarding contract.
3. **Add validator for rules payload** — Validate structure of gold rule set (e.g. `generated_week_scheduler_rules`, `deload_rules`) expected by rules_runtime.
4. **Add pytest that runs validators on gold artifacts** — Test(s) that run validators on `programs/gold/*.json` and `docs/rules/gold/*.rules.json`; assert no errors (or only allowed warnings). Add one or two invalid fixtures and assert expected diagnostics.
5. **Optional: CI or script** — Wire validators into `scripts/` or CI so new/changed artifacts are checked; optional report under `docs/validation/`.
6. **Doc update** — Short "How to run schema validation" in Canonical_Program_Schema or `docs/validation/README.md`.

## Validation

- `pytest` for new validation tests passes.
- Gold artifacts pass; invalid fixtures fail with clear messages.
- No change to runtime load behavior unless load-time strictness is explicitly added later.
