# GPT-5-mini Execution Backlog - Adaptive Coaching Rebuild

Last updated: 2026-03-06

## Priority 0 - Foundation (In Progress)

### Task 0.1 - Ingestion-Centered Architecture Audit
- Identify code to keep/isolate/deprecate/delete.
- Deliver explicit list with file paths and rationale.
- Status: DONE (`docs/redesign/Architecture_Audit_Matrix.md`)

### Task 0.2 - Canonical Schema Finalization
- Finalize typed contracts for templates/catalog/rules/user state.
- Add schema validation tests.
- Status: STARTED (`apps/api/app/adaptive_schema.py`, `apps/api/tests/test_adaptive_gold_schema_contract.py`)

### Task 0.3 - Gold Sample Pair
- Build one manually validated gold program + matching rule set.
- Status: STARTED (`programs/gold/*`, `docs/rules/gold/*`)

### Task 0.4 - Onboarding Package Domain Store
- Maintain one onboarding package per runtime template id.
- Validate package schema and loader stability.
- Status: STARTED

Evidence (2026-03-06)
- `apps/api/app/program_loader.py`: onboarding package loaders + runtime catalog filter for canonical templates.
- `apps/api/tests/test_program_onboarding_contract.py`: package contract and loader tests.

## Priority 1 - Importer and Rules

### Task 1.1 - Excel Importer v2
- Preserve phase/week/day/slot fidelity.
- Preserve warmups/work sets/videos/notes.
- Emit ambiguity diagnostics.

### Task 1.2 - PDF Rule Distillation v1
- Convert doctrine to typed deterministic rules.
- Link rules to source references.

## Priority 2 - Decision Engine Gold Flow

### Task 2.1 - Deterministic Adaptation Core
- Workout generation from template + rules + state.
- Post-session evaluation and next-session adaptation.
- Status: STARTED

Evidence (2026-03-06)
- `packages/core-engine/core_engine/onboarding_adaptation.py`: deterministic adaptation decisions (`preserve/combine/rotate/reduce`).
- `apps/api/app/routers/plan.py`: `POST /plan/adaptation/preview` wired to onboarding package + user weak-area overlay.
- `apps/api/tests/test_program_frequency_adaptation_api.py`: API coverage for deterministic adaptation preview.
- `packages/core-engine/tests/test_onboarding_adaptation.py`: core adaptation tests for target day changes.

### Task 2.2 - Gold End-To-End Runtime Path
- Selection -> generation -> logging -> evaluation -> adaptation.
- Status: STARTED

Evidence (2026-03-06)
- `apps/api/app/routers/plan.py`: `POST /plan/adaptation/apply` persists temporary adaptation state.
- `apps/api/app/routers/plan.py`: `POST /plan/generate-week` consumes active adaptation state and applies temporary day-frequency reduction.
- `apps/api/tests/test_program_frequency_adaptation_api.py`: apply + generate-week countdown coverage.
- `apps/web/app/settings/page.tsx`: UI wiring for adaptation preview and apply actions.

## Priority 3 - Scale and Hardening

### Task 3.1 - Program Library Migration
- Expand canonical migration beyond gold sample.

### Task 3.2 - Scenario and Regression Expansion
- Add scenario suite for progression/fatigue/deload/substitution behavior.

### Task 3.3 - Import Archive Hygiene
- Keep imported template variants available for audit, not runtime selection.
- Status: STARTED

Evidence (2026-03-06)
- Imported templates moved to `programs/archive_imports/` with `programs/archive_imports/README.md`.
- Runtime catalog filtered in `apps/api/app/program_loader.py` to exclude archive/import variants.
