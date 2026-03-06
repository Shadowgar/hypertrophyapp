# Working Agreements - Adaptive Coaching Program

Last updated: 2026-03-06

## Product Integrity Rules

1. Excel is the primary structured source for templates.
2. PDF is the primary doctrine source for rules.
3. Runtime uses canonical templates/rules only.
4. Ingestion artifacts are not runtime behavior.

## Engineering Rules

1. No runtime PDF/XLSX parsing.
2. No free-form chatbot coaching in place of typed rules.
3. Every adaptation decision must be explainable and testable.
4. Import ambiguity must be surfaced, not guessed.
5. Schema changes require versioning + migration notes.

## Commit and Review Rules

- Keep commits scope-focused (schema/importer/rules/runtime/ui).
- Update docs with every contract-level change.
- Include deterministic tests for rule behavior changes.

## Release Gate Rules

- Green validation (`mini_validate`) required.
- Gold sample end-to-end flow must pass before scaling library migration.
- Audit/checklist statuses must map to real evidence paths.
