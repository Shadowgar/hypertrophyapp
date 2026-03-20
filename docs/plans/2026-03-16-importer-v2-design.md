# Excel-First Canonical Importer v2 — Design

**Date:** 2026-03-16  
**Status:** Historical design record. Importer v2 baseline has been implemented; this document is retained for provenance and intent only.  
**Goal:** Define scope, inputs, outputs, and relationship to existing importers so a single canonical importer can produce program templates and onboarding packages with full phase/week/day/slot fidelity per [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md).

## Context

- [Architecture_Audit_Matrix](docs/redesign/Architecture_Audit_Matrix.md) requires: "Implement importer v2 contracts from `docs/contracts/Canonical_Program_Schema.md`."
- [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md) defines Program Template (program_id, phases[], Phase → weeks[], Week → days[], Day → slots[], Slot with exercise_id, warmup_prescription, work_sets, notes), Exercise Catalog Contract, and Coaching Rules Contract. Validation rules: "Importers must fail or emit explicit ambiguity diagnostics when required fields are missing."
- Current importers:
  - `xlsx_to_program.py` — Transitional XLSX parser; emits program JSON with `import_diagnostics`; does not guarantee full phase/week/day/slot structure; kept for build-time only.
  - `xlsx_to_program_v2.py` — Uses [structured_program_builder](importers/structured_program_builder.py); emits [AdaptiveGoldProgramTemplate](apps/api/app/adaptive_schema.py) and sidecar import report; used for gold template generation.
  - `xlsx_to_onboarding_v2.py` — Emits [ProgramOnboardingPackage](apps/api/app/adaptive_schema.py) for one program; validates against app-level schemas.
- Gap: No single build-time pipeline that (1) reads Excel as source of truth, (2) outputs both runtime template and onboarding package with strict phase/week/day/slot fidelity and no silent loss, and (3) conforms to Canonical_Program_Schema and emits explicit diagnostics for ambiguity.

## Scope

### Inputs

- **Primary:** XLSX workbook(s) (one file per program or one file with multiple sheets per phase/week). Structure may follow existing conventions (session labels, block/phase headers, exercise rows) used by `xlsx_to_program` and `structured_program_builder`.
- **Optional:** Existing JSON from current v1/v2 importers for migration or comparison; config (program_id, program_name, phase names, output paths).

### Outputs

1. **Program template JSON** — Written to `programs/` or a designated output dir. Must conform to Canonical_Program_Schema Program Template: program_id, program_name, version, source_workbook, split, phases[] with phase_id/phase_name/intent, each phase weeks[] with week_index and days[], each day day_id/day_name/slots[], each slot slot_id, order_index, exercise_id, optional video_url, warmup_prescription[], work_sets[], notes. All required fields present or explicit diagnostic.
2. **Onboarding package JSON (optional)** — When the pipeline supports onboarding output, same alignment: program_id consistent with template, week-sequence to week-template mapping, day/slot uniqueness. Conforms to ProgramOnboardingPackage and loader expectations.
3. **Import report / diagnostics** — Machine-readable (e.g. JSON) list of { path, code, message } for ambiguity, missing required fields, or fallbacks applied. No silent guessing; every default or skip must be reported.

### Fidelity

- **Phase/week/day/slot:** Workbook structure (phases, blocks, weeks, days) must map 1:1 to canonical phase → weeks → days → slots. No flattening that loses structure. If the workbook has "Phase 1, Week 1–4, Week 5 deload", the output must reflect that.
- **Exercise identity:** Every slot has a canonical exercise_id (resolved via catalog or explicit mapping). Unknown exercises produce a diagnostic, not a synthetic ID.
- **Prescriptions:** Warmup and work_sets preserved per slot; rep_target, set_type, optional rpe_target/load_target per Canonical_Program_Schema.

### Relation to existing importers

- **xlsx_to_program.py:** Remain as transitional parser until importer v2 is validated on at least one gold program. Then deprecate or restrict to legacy one-off imports; v2 becomes the default for new programs.
- **xlsx_to_program_v2.py** and **structured_program_builder:** Reuse or refactor. v2 design can be "extend v2 + structured_program_builder to full canonical output and diagnostics" rather than a rewrite. Clarify which parts of structured_program_builder become the canonical pipeline and which are legacy.
- **xlsx_to_onboarding_v2.py:** Either (a) folded into the same pipeline (one entrypoint produces both template and onboarding) or (b) kept as separate step that consumes the v2 template output. Design choice: single entrypoint vs two-step (template then onboarding from template).

## Out of scope

- PDF parsing or doctrine extraction (handled by PDF-to-rules workflow).
- Runtime loading or API changes (loader already consumes JSON; importer is build-time only).
- Support for non-Excel sources in v2 (e.g. CSV, manual JSON) unless explicitly added later.

## Success criteria

- One or more programs (starting with gold) can be produced from XLSX via the v2 pipeline with full phase/week/day/slot fidelity.
- Output passes schema validation (see [2026-03-16-schema-validation-design.md](2026-03-16-schema-validation-design.md)).
- Every ambiguity or missing required field produces an explicit diagnostic; no silent defaults for structural or identity fields.
- Documentation: how to run the importer v2, how to interpret the report, and how it relates to Canonical_Program_Schema and existing importers.

## Implementation plan

See `docs/plans/2026-03-16-importer-v2-implementation.md` (to be created via writing-plans after this design is approved).
