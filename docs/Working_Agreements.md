# Working Agreements - Adaptive Coaching Program

Last updated: 2026-03-07

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

## Decision Runtime Rules

1. No new meaningful coaching behavior outside `packages/core-engine`.
2. Preview and apply must share one interpreter per decision family.
3. Routers orchestrate IO and persistence only.
4. Explanations must come from interpreter output.
5. Every meaningful coaching decision must emit a structured decision trace.
6. Legacy runtime paths may exist temporarily, but may not receive new coaching logic.
7. Programs without canonical artifacts are legacy, not first-class runtime programs.

## Commit and Review Rules

- Keep commits scope-focused (schema/importer/rules/runtime/ui).
- Update docs with every contract-level change.
- Include deterministic tests for rule behavior changes.

## Release Gate Rules

- Green validation (`mini_validate`) required.
- Gold sample end-to-end flow must pass before scaling library migration.
- Audit/checklist statuses must map to real evidence paths.
