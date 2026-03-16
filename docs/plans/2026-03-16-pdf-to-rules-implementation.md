# PDF-to-Rules Distillation — Implementation Plan

**Date:** 2026-03-16  
**Design:** [2026-03-16-pdf-to-rules-design.md](2026-03-16-pdf-to-rules-design.md)

## Tasks

1. **Document current workflow** — Write a short runbook (e.g. in `docs/guides/` or `importers/README`) that describes: reference_corpus_ingest → provenance_index + normalized docs; pdf_doctrine_rules_v1 → reads normalized docs, emits rules JSON. Include how to run each step and where outputs live.
2. **Define provenance format** — Add a standard provenance object shape (source_asset, section, excerpt) to the rule set schema or to AdaptiveGoldRuleSet; ensure pdf_doctrine_rules_v1 (or successor) populates it for each rule/block and that it is persisted in emitted JSON.
3. **Rationale per rule/block** — Ensure every emitted rule or logical block has a rationale field (or rationale_templates reference); where extraction cannot infer it, use a placeholder and document for manual audit. Align with Canonical_Program_Schema rationale_templates.
4. **Validate output** — Run distillation on gold source(s); ensure output passes schema validation (see schema-validation design). Confirm rules_runtime can load the emitted JSON.
5. **Optional: CI or report** — Add script or CI step that runs distillation and produces a small report (rules emitted, sections matched/unmatched); or integrate into existing ingestion_quality_report / validation.
6. **Doc update** — Link workflow runbook from Master_Plan Phase C and from Canonical_Program_Schema (Coaching Rules Contract).

## Validation

- Gold rule set(s) produced from PDF-derived docs pass schema validation.
- Provenance and rationale fields are present and documented.
- Runtime loader can load the emitted rules without change.
