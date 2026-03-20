# PDF-to-Rules Distillation Workflow — Design

**Date:** 2026-03-16  
**Status:** Historical design record. Initial implementation completed in Phase C; keep for provenance, not active execution authority.  
**Goal:** Define the workflow, tooling, and output format for distilling PDF coaching doctrine into typed rules with explainable rationale and provenance links to source sections.

## Context

- Master_Plan Phase C: "Implement PDF-to-rules distillation workflow (typed rules, explainable rationale). Add provenance links from rules to source sections."
- [Canonical_Program_Schema](docs/contracts/Canonical_Program_Schema.md) defines the Coaching Rules Contract (rule_set_id, program_scope, starting_load_rules, progression_rules, deload_rules, phase_transition_rules, substitution_rules, generated_week_scheduler_rules, rationale_templates).
- Current state: [pdf_doctrine_rules_v1.py](importers/pdf_doctrine_rules_v1.py) exists — build-time script that reads normalized guide docs (via [provenance_index](docs/guides/provenance_index.json)), extracts patterns, and emits [AdaptiveGoldRuleSet](apps/api/app/adaptive_schema.py) with optional source excerpts. [reference_corpus_ingest](importers/reference_corpus_ingest.py) produces normalized markdown from PDFs; output is under docs/guides/generated.
- Gap: Workflow is not fully documented; "provenance links from rules to source sections" may mean stable references (e.g. section IDs, page or heading) so each rule can point back to the PDF/section it was derived from; rationale may need to be explicit per-rule or per-block.

## Scope

### Workflow

1. **Source:** PDF manuals (in `reference/` or similar). Primary doctrine source per Master_Plan.
2. **Normalization:** Existing pipeline (reference_corpus_ingest) produces normalized text/markdown under docs/guides; provenance_index maps source PDF to derived paths. No runtime dependency on raw PDFs.
3. **Distillation:** Script (current pdf_doctrine_rules_v1 or successor) reads normalized docs, applies pattern/heuristic extraction for starting load, progression, deload, substitution, scheduler behavior, and emits typed rule payloads.
4. **Output:** JSON rule set(s) under `docs/rules/` (e.g. `docs/rules/gold/*.rules.json`, `docs/rules/canonical/*.rules.json`) conforming to Coaching Rules Contract. Each rule or rule block can carry:
   - **Rationale:** Human-readable explainable rationale (e.g. "Leave 1–2 reps in reserve for working sets").
   - **Provenance:** Link to source (e.g. source_asset, section_heading, or excerpt path) so support/debugging can trace back to the manual.

### Typed rules and explainable rationale

- **Typed:** Rule payloads are structured (not free text); fields align with rules_runtime expectations (e.g. generated_week_scheduler_rules.mesocycle, deload_rules, substitution_rules). Rationale can live in a `rationale` or `rationale_templates` field per Canonical_Program_Schema.
- **Explainable:** Every emitted rule or block should have a short rationale (or reference to a rationale template) so that traces and UI can show "why" this rule applies. If extraction cannot infer rationale, emit a placeholder and document it as manual-audit required.

### Provenance links

- **Per rule or per block:** Each rule (or logical group) should reference source: e.g. `source_asset: "program_manual.pdf"`, `section: "Progression"`, optional `excerpt_path` or `excerpt_text` (snippet). Format can be a small object: `{ "source_asset": string, "section": string?, "excerpt": string? }`.
- **Stored in output:** Provenance stored in the emitted JSON so that tooling or UI can "show source" without re-parsing PDFs.

### Tooling

- **Build-time only:** All PDF reading and distillation runs in scripts/importers; never in API or runtime.
- **CLI/script:** Single entrypoint (e.g. `python importers/pdf_doctrine_rules_v1.py ...` or a wrapper) that accepts source PDF or normalized doc path and output path; writes rules JSON and optional report (e.g. rules emitted, sections matched, sections with no match).
- **CI/validation:** Optional step that runs distillation on known PDFs and diffs output to catch regressions; or run as part of reference corpus ingest.

## Out of scope

- Runtime interpretation of PDF or raw text (runtime consumes only typed rules JSON).
- Full NLP or LLM-based extraction unless explicitly added later; current design assumes pattern/heuristic extraction with optional manual curation.
- Editing PDFs or changing source format; workflow consumes existing reference corpus pipeline.

## Success criteria

- Workflow is documented: steps (normalize → distill → output), inputs/outputs, how to run the script(s).
- At least one rule set (e.g. gold) is produced from PDF-derived normalized docs with typed rules and rationale; output passes schema validation.
- Provenance: each rule or block includes source reference (asset + section or excerpt); format documented.
- Optional: CI or script that runs distillation and reports coverage (e.g. sections with no matching rules).

## Implementation plan

See `docs/plans/2026-03-16-pdf-to-rules-implementation.md` (to be created via writing-plans after this design is approved).
