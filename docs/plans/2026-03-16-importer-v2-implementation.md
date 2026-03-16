# Excel-First Canonical Importer v2 — Implementation Plan

**Date:** 2026-03-16  
**Design:** [2026-03-16-importer-v2-design.md](2026-03-16-importer-v2-design.md)

## Tasks

1. **Define v2 entrypoint and output contract** — Single script or CLI (e.g. `importers/xlsx_to_canonical_v2.py` or extend existing v2) that accepts XLSX path and program_id; outputs program template JSON and optional onboarding JSON plus diagnostics report. Align output schema with Canonical_Program_Schema and existing AdaptiveGoldProgramTemplate/ProgramOnboardingPackage where applicable.
2. **Implement phase/week/day/slot extraction** — Reuse or refactor structured_program_builder and xlsx_to_program parsing so that workbook structure maps to canonical phases → weeks → days → slots without flattening. Emit diagnostics for any ambiguous or missing structural field.
3. **Exercise ID resolution** — Resolve every slot to a canonical exercise_id (catalog or explicit map); emit diagnostic for unknowns instead of inventing IDs.
4. **Prescriptions and metadata** — Preserve warmup_prescription and work_sets per slot; include source_workbook, version, split. Emit diagnostics for missing or ambiguous prescriptions.
5. **Onboarding package path** — Either integrate onboarding generation into the same pipeline (from template + workbook) or add a second step that builds onboarding from v2 template output; document the chosen approach.
6. **Validate on gold** — Run v2 on the gold workbook(s) used for Pure Bodybuilding Phase 1; compare output to existing gold JSON; ensure schema validation passes and diagnostics are acceptable.
7. **Documentation** — Add runbook: how to run importer v2, how to read the report, relation to Canonical_Program_Schema and existing importers. Update Architecture_Audit_Matrix when v2 is the default.

## Validation

- Gold program(s) produced from XLSX pass schema validation tests.
- Diagnostics report is generated and documented; no silent structural or identity defaults.
- Existing API/loader can load the v2-produced JSON without change (contract compatibility).
