# Exercise Metadata Quality Audit

## A. Coverage Summary by Metadata Type
- movement_pattern: 1173/2302 present (50.96%), 1104 null (47.96%), 25 missing key (1.09%).
- substitution_metadata: 0/2302 exercises with authored substitution metadata.
- equipment token drift: 0 non-canonical/synonym tokens detected.

## B. Exact Files/Locations with Missing or Inconsistent Metadata
- movement pattern gaps: see `gaps.movement_pattern_missing_examples` and `gaps.movement_pattern_coverage_by_file` in JSON output.
- equipment drift: see `gaps.equipment_drift_examples` and `coverage_summary.equipment_tags.non_canonical_or_synonym_tokens`.
- substitution completeness/fallback gaps: see `gaps.high_risk_empty_substitution_candidates`, `gaps.placeholder_substitution_candidates`, and `gaps.sparse_candidate_metadata_examples`.

## C. Severity Ranking
- blocks safe runtime decisions:
  - Missing candidate movement_pattern metadata can bypass restriction filtering.
  - High-risk movement patterns with empty substitution_candidates can cause unsafe drops/no fallback.
  - Placeholder/stale substitution identifiers degrade to low-confidence fallback behavior.
- weakens decision quality:
  - Equipment synonym drift and sparse equipment tags increase inference dependence.
  - Missing candidate primary_muscles weakens weak-area routing and tie-break confidence.
- mostly cosmetic:
  - Missing candidate video metadata lowers coaching payload quality but not safety in most paths.

## D. Recommended Next Implementation Plan
1. Define canonical movement_pattern and equipment tag vocabularies.
2. Create metadata validator and fail-on-regression CI checks for active templates.
3. Backfill substitution metadata for active templates (id, movement_pattern, equipment_tags, primary_muscles).
4. Add sparse-metadata restriction policy (allow/deny/warn) with trace confidence flags.
5. Normalize template-side equipment tokens and remove synonym drift at source.
6. Remediate high-risk imported templates with empty substitution candidates for restricted patterns.
7. Add regression tests for restriction leaks, substitution quality, and weak-area classification confidence.

## E. Next Phase Decision
- keep phase: True
- recommended phase: exercise metadata hardening for safe program expansion
- reason: Current runtime safety and quality now directly depend on metadata coverage and consistency.
