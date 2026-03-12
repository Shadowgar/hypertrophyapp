# Architecture Audit Matrix - Phase A

Last updated: 2026-03-06

Purpose: classify ingestion-centered and adjacent modules into keep/isolate/deprecate/delete so the adaptive runtime remains deterministic and independent from raw source parsing artifacts.

## Keep

| Path | Why keep | Required follow-up |
| --- | --- | --- |
| `importers/xlsx_to_program.py` | Build-time XLSX importer and normalization entrypoint. | Implement importer v2 contracts from `docs/contracts/Canonical_Program_Schema.md`. |
| `importers/reference_corpus_ingest.py` | Build-time provenance catalog generation from `/reference`. | Keep output as provenance only; do not expose as runtime coaching input. |
| `importers/ingestion_quality_report.py` | Quality diagnostics for canonical program coverage. | Extend with v2 schema conformance metrics. |
| `scripts/generate_ingestion_quality_report.py` | Deterministic generation of report artifacts in `docs/validation/`. | Keep in CI/local validation path. |
| `apps/api/app/routers/plan.py` (coach preview/apply/timeline routes) | Active runtime coaching endpoints that should evolve to canonical rules/state contracts. | Rewire internals to use explicit rules engine v2. |
| `apps/web/components/coaching-intelligence-panel.tsx` and `apps/web/app/history/page.tsx` | Current UX surfaces for explainable recommendations and timeline visibility. | Preserve UX behavior while swapping backend decision source to canonical rules layer. |

## Isolate

| Path | Isolation boundary | Required follow-up |
| --- | --- | --- |
| `docs/guides/generated/*.md` | Reference artifact only; never used in runtime request path. | Keep generation for provenance/debug only. |
| `docs/guides/asset_catalog.json` | Build-time metadata index only. | Treat as offline audit data only. |
| `docs/guides/provenance_index.json` | Build-time provenance index only. | No runtime endpoint should read this file. |
| `scripts/reference_ingest.sh` | Ingestion orchestration script for CI/local generation. | Keep out of runtime images and request handling logic. |
| `scripts/verify_guides_checksums.py` | Verification utility for generated guide outputs. | Continue to run in validation workflows only. |
| `docs/guides/FULL_EXTRACTION_RUNBOOK.md` | Operator runbook, not runtime behavior. | Keep aligned with extraction-failure policy and exceptions. |

## Deprecate

| Path | Deprecation reason | Action taken |
| --- | --- | --- |
| `apps/api/app/routers/plan.py` route `/plan/intelligence/reference-pairs` | Runtime endpoint read `docs/guides/provenance_index.json`, creating guide-artifact coupling. | Removed route on 2026-03-06. |
| `apps/web/lib/api.ts` `listReferencePairs` + `ReferenceWorkbookGuidePair` | Client contract depended on deprecated runtime endpoint. | Removed on 2026-03-06. |
| `apps/web/app/settings/page.tsx` reference pair counter | Settings UI depended on deprecated endpoint for ingestion metadata. | Removed on 2026-03-06. |
| `apps/api/tests/test_plan_intelligence_api.py` reference-pairs test | Covered deprecated endpoint behavior only. | Removed on 2026-03-06. |
| `apps/web/tests/settings.intelligence.test.tsx` reference-pairs fetch mock | Test fixture for deprecated endpoint. | Removed on 2026-03-06. |

## Delete

No hard deletes in this phase. Preserve history while deprecations settle and replacements are validated.

## Exit Criteria For Phase A

- No API/web runtime code reads `docs/guides/*` artifacts directly.
- Ingestion/reporting artifacts remain available only for offline provenance and QA workflows.
- Deprecation list is published and referenced by planning docs.
