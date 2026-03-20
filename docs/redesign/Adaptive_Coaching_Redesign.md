# Adaptive Coaching Redesign (Authoritative)

Last updated: 2026-03-16
Status: Active redesign directive

## 1. Revised Architecture

Rocco's HyperTrophy is a structured adaptive coaching platform, not a document text ingestion product.

Runtime architecture:

1. Program Template Layer (Excel-derived canonical structure)
2. Coaching Rules Layer (PDF-derived explicit rule objects)
3. Exercise Knowledge Layer (stable exercise catalog)
4. User Training State Layer (logs, fatigue, progression state)
5. Decision Engine (deterministic adaptation)
6. Product/UI Layer (selection, execution, coaching feedback)

Build-time architecture:

1. Excel importer pipeline -> canonical templates
2. PDF doctrine distillation pipeline -> typed coaching rules
3. Validation + provenance pipeline -> quality gates

Hard boundary:
- Runtime must not parse raw PDF/XLSX.
- Runtime must not depend on text dumps of source manuals.

## 2. Canonical Data Schema (Summary)

### Program Template
- program_id
- program_name
- source_workbook
- phases[]
  - phase_id
  - phase_name
  - weeks[]
    - week_index
    - days[]
      - day_id
      - day_name
      - slots[]
        - slot_id
        - order_index
        - exercise_id
        - video_url
        - warmup_prescription
        - work_sets[]
        - rep_target
        - rir_target or rpe_target
        - notes

### Exercise Catalog
- exercise_id (stable)
- canonical_name
- aliases[]
- movement_pattern
- primary_muscles[]
- secondary_muscles[]
- equipment_type[]
- default_video_url
- substitutions[]

### Coaching Rules
- rule_set_id
- source_pdf
- program_scope
- starting_load_rules
- progression_rules
- underperformance_rules
- fatigue_rules
- deload_rules
- phase_transition_rules
- substitution_rules
- rationale_templates

### User Training State
- user_program_state (program, phase, week, day pointers)
- exercise_performance_history
- progression_state_per_exercise
- fatigue_state
- adherence_state
- stall_state

## 3. Excel Importer Design

Goals:
- Parse workbook structure into canonical program object without guessing hidden intent.
- Preserve exercise order, videos, warmups, work sets, reps, and notes.
- Emit explicit ambiguity warnings when fields are missing or conflicting.

Pipeline:
1. Workbook loader -> sheets/tables
2. Structural parser -> phase/week/day/slot extraction
3. Slot parser -> warmups, work sets, reps, effort targets
4. Exercise resolver -> map names to stable exercise IDs
5. Validation stage -> reject malformed or ambiguous templates
6. Canonical emitter -> `programs/canonical/*.json`
7. Quality report -> `docs/validation/import_quality_report.json`

## 4. PDF Rule Extraction Workflow

Goals:
- Convert manual doctrine into explicit rules, not runtime free text.
- Produce explainable and testable rule objects.

Workflow:
1. Manual curation pass (human-assisted extraction)
2. Rule statement drafting in structured template
3. Normalize statements into typed fields
4. Cross-check with source references
5. Rule simulation tests against synthetic scenarios
6. Emit canonical rules JSON -> `docs/rules/canonical/*.rules.json`

Rule quality gates:
- No unresolved placeholders
- Every rule has deterministic trigger + action + rationale
- Every rule links to source section metadata

## 5. File/Folder Structure (Current)

- `programs/gold/` (runtime-ready templates; `pure_bodybuilding_phase_1_full_body` is the active administered program)
- `docs/rules/canonical/` (runtime coaching rules)
- `docs/rules/gold/` (gold-path coaching rules)
- `packages/core-engine/core_engine/decision_*.py` (decision-family owners: generated_week, progression, weekly_review, workout_session, coach_preview, frequency_adaptation, program_recommendation, live_workout_guidance)
- `packages/core-engine/core_engine/rules_runtime.py` (doctrine substrate)
- `packages/core-engine/core_engine/scheduler.py` (execution engine)
- `packages/core-engine/core_engine/user_state.py` (canonical user training state assembly)
- `packages/core-engine/core_engine/generation.py` (generation runtime orchestration)
- `packages/core-engine/core_engine/intelligence.py` (orchestration-only compatibility façade)
- `apps/api/app/program_loader.py` (program template loading and resolution)
- `apps/api/app/routers/` (API route orchestration)
- `docs/redesign/` (architecture and migration artifacts)

## 6. Migration Plan From Current Approach

Stage 1: Isolate ingestion artifacts from runtime paths
- Keep `docs/guides/generated/*.md` as reference-only outputs.
- Remove any product assumptions tied to text excerpt availability.

Stage 2: Establish canonical schema and one gold program
- Implement strict schema and one validated program/rules pair.

Stage 3: Wire runtime to schema + rules only
- Runtime week/day generation must read canonical program + rules, not ingestion markdown.

Stage 4: Expand catalog incrementally
- Migrate each program workbook manually/semiautomatically through validation gate.

Stage 5: Deprecate legacy adapters
- Remove or freeze ingestion paths that output non-runtime blobs.

## 7. Gold-Standard Samples

The active administered program is Hypertrophy Phase 1:
- `programs/gold/pure_bodybuilding_phase_1_full_body.json` (canonical program template)
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` (onboarding package with authored slot fields)
- `docs/rules/canonical/pure_bodybuilding_phase_1_full_body.rules.json` (canonical coaching rules)

The adaptive gold sample remains as a compatibility baseline:
- `programs/gold/adaptive_full_body_gold_v0_1.json`
- `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json`

The administered program is the baseline for end-to-end runtime implementation and dogfooding.

## 8. First-Pass Deterministic Progression Logic

Per exercise exposure:
1. If all work sets hit top of rep range with acceptable effort -> increase load next exposure.
2. If reps are within range but not at top -> hold load, chase reps.
3. If repeated under-target performance for two exposures -> reduce load or repeat microcycle.
4. If global fatigue flags breach threshold -> reduce volume and/or deload.
5. Log rationale on every action for explainability.

## 9. Explicit Delete/Deprecate/Isolate List

Isolate (build-time only, not runtime dependencies):
- `importers/reference_corpus_ingest.py` outputs in `docs/guides/generated/*.md`
- `docs/guides/asset_catalog.json` and `docs/guides/provenance_index.json` as runtime inputs

Deprecate in product UX context:
- Any UI/API workflow that treats reference-pair listing as coaching intelligence source

Keep but re-scope:
- `importers/xlsx_to_program.py` as transitional parser until canonical importer v2 lands
- Existing intelligence endpoints as provisional behavior pending rule-layer refactor

## Immediate Start Sequence

1. Complete schema definitions for Program Template, Exercise Catalog, Coaching Rules.
2. Create one gold sample from one workbook + matching manual.
3. Build decision engine flow only for this gold sample.
4. Validate end-to-end: selection -> workout -> logging -> evaluation -> adaptation.
5. Scale only after this path is deterministic and test-covered.
