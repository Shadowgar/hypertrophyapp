# Exercise Metadata Quality Audit Handoff

## A. Coverage Summary by Metadata Type

- `movement_pattern` (template exercises): `1173/2302` present (`50.96%`), `1104/2302` null (`47.96%`), `25/2302` missing key (`1.09%`).
- `substitution_candidates`: `2302/2302` exercises have candidates (`100%`).
- Authored `substitution_metadata`: `0/2302` template exercises (`0%`) in standard program template JSONs.
- Runtime-dependent exercise fields:
  - `primary_muscles`: `1123` present / `1179` missing.
  - `equipment_tags`: `233` present / `2069` missing.
  - `slot_role`: `68` present / `2234` missing.
- Equipment token consistency:
  - Exercise-level distinct tokens: `barbell`, `bench`, `cable`, `dumbbell`, `machine`, `rack`.
  - Global token drift detected: `bar -> barbell` (1 occurrence).
  - UI inputs (`onboarding`/`settings`) expose: `barbell`, `bench`, `dumbbell`, `cable`, `machine`, `bands`, `bodyweight` (no `rack` option).

## B. Exact Files/Locations with Missing or Inconsistent Metadata

- Movement pattern missing/null hotspots:
  - `programs/archive_imports/pure_bodybuilding_phase_2___ppl_sheet_imported.json` (`116/116` missing/null)
  - `programs/archive_imports/pure_bodybuilding_phase_2___upper_lower_sheet_imported.json` (`86/86` missing/null)
  - `programs/archive_imports/pure_bodybuilding_phase_2___full_body_sheet_imported.json` (`86/86` missing/null)
  - `programs/archive_imports/pure_bodybuilding_phase_2___full_body_sheet_(1)_imported.json` (`86/86` missing/null)
  - `programs/archive_imports/pure_bodybuilding___full_body_imported.json` (`85/85` missing/null)
  - `programs/archive_imports/the_bodybuilding_transformation_system___beginner_imported.json` (`76/76` missing/null)
  - `programs/archive_imports/the_bodybuilding_transformation_system___intermediate_advanced_imported.json` (`75/75` missing/null)
  - `programs/full_body_v1.json` (25 exercises missing `movement_pattern` key)
- Equipment consistency / synonym drift:
  - `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` (`equipment_tags` includes non-canonical `bar` at least once)
  - `programs/ppl_v1.json` and `programs/upper_lower_v1.json` use `rack` while UI inputs do not expose `rack`
  - `apps/web/app/onboarding/page.tsx` and `apps/web/app/settings/page.tsx` equipment options diverge from template vocabulary
- Substitution completeness/fallback quality:
  - `programs/archive_imports/powerbuilding_3.0_imported.json`: `37` high-risk patterns (`squat`, `lunge`, `vertical_press`) with empty substitution candidates
  - `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`: placeholder substitution references (`see_the_weak_point_table_for_sub_options`) appear in `valid_substitutions`
  - Runtime fallback points:
    - `packages/core-engine/core_engine/rules_runtime.py`
    - `packages/core-engine/core_engine/scheduler.py`
    - `apps/api/app/program_loader.py`

## C. Severity Ranking

- **Blocks safe runtime decisions**
  - Missing candidate `movement_pattern` metadata for substitutions can bypass restriction filtering.
  - Empty substitution candidate lists on high-risk patterns can produce unsafe drops/no fallback.
  - Placeholder substitution identifiers degrade to low-confidence fallback behavior.
- **Weakens decision quality**
  - Equipment vocabulary drift (`bar`/`barbell`, UI-vs-template mismatch for `rack`) increases mismatch risk.
  - Sparse `equipment_tags` and sparse `primary_muscles` force lower-confidence inference for compatibility and weak-area logic.
  - Low `slot_role` coverage weakens deterministic priority behavior under compression/caps.
- **Mostly cosmetic**
  - Missing candidate video metadata (quality issue, usually not safety-critical).

## D. Recommended Next Implementation Plan

1. Define canonical vocabularies for `movement_pattern`, `equipment_tags`, and substitution metadata schema.
2. Add a metadata validator for active templates with CI fail-on-regression gates.
3. Backfill active templates so each substitution candidate has metadata (`id`, `movement_pattern`, `equipment_tags`, `primary_muscles`).
4. Add explicit sparse-metadata restriction policy (`allow`/`deny`/`warn`) and trace confidence fields.
5. Normalize template-side equipment tokens to canonical forms and align UI/profile vocabulary.
6. Remediate high-risk imported templates (starting with `powerbuilding_3.0_imported.json`) for restricted-pattern fallback coverage.
7. Add regression tests for restriction leaks, substitution quality, equipment matching, and weak-area classification confidence.

## E. Next Phase Decision

- Keep next phase as: **exercise metadata hardening for safe program expansion**.
- Rationale: runtime safety/quality now depends directly on metadata completeness and consistency; current highest residual risk is metadata-driven (restriction leaks, bad substitutions, mismatch, low trace confidence), not new algorithmic features.
