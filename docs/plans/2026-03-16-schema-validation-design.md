# Schema Validation — Design

**Date:** 2026-03-16  
**Status:** Design; implementation pending  
**Goal:** Scope "strict schema validation tests" and "ambiguity/error reporting" so implementation does not drift or over-build.

## Context

- [Canonical_Program_Schema.md](docs/contracts/Canonical_Program_Schema.md) defines the runtime contract for program templates, phases/weeks/days/slots, exercise catalog, coaching rules, and user training state.
- Master_Plan Phase B has an unchecked item: "Add strict schema validation tests and ambiguity/error reporting."
- Current state: API uses Pydantic models ([adaptive_schema.py](apps/api/app/adaptive_schema.py), [template_schema.py](apps/api/app/template_schema.py)) for load-time validation; importers emit `import_diagnostics`; there is no single test suite that asserts canonical schema conformance for all artifact types.

## Scope

### What is validated

1. **Program templates (runtime)** — JSON under `programs/` consumed by the loader.  
   - Required: `program_id`, `program_name`, structure of phases/weeks/days/slots per Canonical_Program_Schema.  
   - Optional but tracked: `source_workbook`, slot-level fields (e.g. `slot_role`, warmup/work_sets), exercise_id resolution.

2. **Onboarding packages** — JSON under `programs/` (e.g. `*.onboarding.json`).  
   - Required: alignment of `program_id` across package, blueprint, and intent; week-sequence entries mapping to declared week-template IDs; day slot IDs and order indices unique per day (per Master_Plan delivery delta).  
   - Contract: [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md) plus onboarding-specific constraints used by [program_loader](apps/api/app/program_loader.py) and onboarding APIs.

3. **Coaching rules** — Typed rule payloads under `docs/rules/` (e.g. `*.rules.json`).  
   - Required: structure expected by [rules_runtime](packages/core-engine/core_engine/rules_runtime.py) (rule_set_id, program_scope, generated_week_scheduler_rules, deload_rules, etc.).  
   - Optional: full Coaching Rules Contract from Canonical_Program_Schema; start with scheduler/deload/substitution blocks used on the gold path.

### Where validation runs

- **Tests only (recommended first):** Pytest (or similar) that loads artifact files from `programs/` and `docs/rules/` and asserts conformance. No runtime load-time change initially.  
- **Build-time (optional later):** Script or CI step that runs the same validators on commit or in CI; fails or reports when new artifacts are added or changed.  
- **Load-time (optional later):** API/loader already use Pydantic; "strict" could mean failing fast on unknown fields or on missing required fields that today are defaulted. Only add if product needs hard fail on invalid artifacts in production.

### Ambiguity and error reporting

- **Ambiguity:** Cases where the schema allows multiple interpretations (e.g. duplicate slot_id, week_index gaps, exercise_id not in catalog). Validators should emit explicit diagnostics (list of { path, code, message }) rather than silent defaults.  
- **Error reporting:**  
  - In tests: assert no errors or no ambiguities for gold artifacts; assert specific errors for intentionally invalid fixtures.  
  - In build-time/CI: emit a small report (e.g. Markdown or JSON) listing file, path, and message for each violation.  
  - Do not invent new UI or logging infrastructure; keep reporting to test output and optional artifact files (e.g. under `docs/validation/`).

## Out of scope

- Runtime validation of user-submitted payloads (already handled by FastAPI/Pydantic).  
- Validation of PDF or XLSX source files (those are build-time importer concerns; importers already emit diagnostics).  
- General-purpose JSON Schema or OpenAPI validation for the whole API.

## Success criteria

- One or more pytest modules that validate at least: (1) gold program template(s), (2) gold onboarding package(s), (3) gold rule set(s) against the canonical contracts.  
- Clear pass/fail: gold artifacts pass; invalid fixtures fail with identifiable messages.  
- Optional: CI step or script that runs these validators and, if desired, writes an ambiguity/error report artifact.  
- Documentation: add a short section to [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md) or a dedicated `docs/validation/README.md` describing how to run validation and how to interpret the report.

## Implementation plan

See `docs/plans/2026-03-16-schema-validation-implementation.md` (to be created via writing-plans after this design is approved).
