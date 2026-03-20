# Next Actions

Last updated: 2026-03-20

This is the short execution rail for the current repo state.

The `Compiled Knowledge Foundation` milestone is complete. There is no new active implementation milestone in this file yet.

## Immediate Actions

1. Read `docs/DECISIONS.md`, `docs/IMPLEMENTATION_PLAN_CURRENT_MILESTONE.md`, and `docs/CURRENT_STATE.md`.
2. Treat the current milestone as closed.
3. Do not begin the next milestone until it is explicitly approved.
4. If additional work is needed before approval, keep it limited to milestone-closeout audits, deterministic hardening, or documentation corrections.

## Verification Commands

- `scripts/reference_ingest.sh ci`
- `cd apps/api && PYTHONPATH=. python3 -m pytest tests/test_reference_corpus_ingestion.py tests/test_runtime_source_boundaries.py tests/test_source_registry_contract.py tests/test_source_to_knowledge_pipeline.py tests/test_exercise_library_contract.py tests/test_knowledge_loader.py -q`
- `./scripts/deterministic_regression_validate.sh`

## Stop Conditions

- stop if the next task is a new milestone that has not been explicitly approved
- stop if a change requires router behavior changes
- stop if a change requires DB model or migration work
- stop if a change requires modifying core-engine behavior
- stop if a change expands into generated-program logic

## Out Of Scope

- any unapproved post-foundation milestone work
- generated-program construction
- policy execution in runtime
- diagnostics runtime
- user-facing transparency UI
- specialization logic
