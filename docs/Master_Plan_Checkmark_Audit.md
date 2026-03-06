# Master Plan Checkmark Audit (Evidence-Based)

Last audited: 2026-03-06
Audit basis: committed `HEAD` on `main`.

Status legend:

- `VERIFIED`: implemented in code and supported by tests/artifacts.
- `PARTIAL`: scaffolding exists but end-to-end behavior is incomplete or low quality.
- `NOT VERIFIED`: claim lacks code/test evidence or conflicts with repository state.

## Executive Summary

- Previous audit style over-reported completion by using broad grouped evidence.
- Several checklist claims are valid in backend engine/API, but not wired end-to-end in product UI.
- Ingestion artifact presence is real, but extraction quality is currently metadata-only in committed outputs.
- Template library quantity is high, but quality is inconsistent for coach-grade runtime behavior.

## Verification Matrix

| Domain | Claim | Status | Evidence |
| --- | --- | --- | --- |
| Runtime determinism | Runtime does not parse PDFs/XLSX in request paths | VERIFIED | `apps/api/app/routers/*.py`, `README.md`, `importers/reference_corpus_ingest.py` |
| Week generation | Deterministic weekly plan generation exists | VERIFIED | `packages/core-engine/core_engine/scheduler.py`, `packages/core-engine/tests/test_scheduler.py` |
| Equipment handling | Equipment-aware substitutions in planning | VERIFIED | `packages/core-engine/core_engine/scheduler.py`, `packages/core-engine/tests/test_scheduler.py` |
| Soreness handling | Soreness modifiers alter recommendations deterministically | VERIFIED | `packages/core-engine/core_engine/scheduler.py`, `packages/core-engine/tests/test_scheduler.py` |
| Mesocycle/deload | Scheduled and early-deload logic exists | VERIFIED | `packages/core-engine/core_engine/scheduler.py`, `packages/core-engine/tests/test_scheduler.py` |
| Workout runner | Set logging + live recommendation loop | VERIFIED | `apps/api/app/routers/workout.py`, `apps/api/tests/test_workout_logset_feedback.py`, `apps/api/tests/test_workout_session_state.py` |
| Weekly review | Prior-week fault scan and adjustments persisted | VERIFIED | `apps/api/app/routers/profile.py`, `apps/api/tests/test_weekly_review.py` |
| Program recommendation | Deterministic recommendation + switch confirmation | VERIFIED | `apps/api/app/routers/profile.py`, `apps/api/tests/test_program_recommendation_and_switch.py` |
| Guide APIs | Program/day/exercise guide drill-down exists | VERIFIED | `apps/api/app/routers/plan.py`, `apps/api/tests/test_plan_guides_api.py` |
| Intelligence preview | `coach-preview` endpoint exists and tested | VERIFIED | `apps/api/app/routers/plan.py`, `apps/api/tests/test_plan_intelligence_api.py` |
| Intelligence apply | Phase + specialization apply endpoints exist and tested | VERIFIED | `apps/api/app/routers/plan.py`, `apps/api/tests/test_plan_intelligence_api.py` |
| Recommendation persistence | Coaching recommendation records persisted | VERIFIED | `apps/api/app/models.py`, `apps/api/alembic/versions/0009_coaching_recommendations.py`, `apps/api/tests/test_plan_intelligence_api.py` |
| Frontend coaching flow | UI consumes `coach-preview` + apply endpoints | VERIFIED | `apps/web/lib/api.ts`, `apps/web/app/settings/page.tsx`, `apps/web/app/week/page.tsx`, `apps/web/app/checkin/page.tsx`, `apps/web/app/today/page.tsx`, `apps/web/components/coaching-intelligence-panel.tsx`, `apps/web/tests/settings.intelligence.test.tsx`, `apps/web/tests/coaching.intelligence.routes.test.tsx` |
| Frontend apply ergonomics | Apply flow can use preview output without manual lookup | VERIFIED | `apps/api/app/schemas.py`, `apps/api/app/routers/plan.py`, `apps/web/app/settings/page.tsx`, `apps/web/tests/settings.intelligence.test.tsx` |
| Recommendation timeline UI | User-visible coaching decision timeline exists | VERIFIED | `apps/api/app/routers/plan.py`, `apps/api/tests/test_plan_intelligence_api.py`, `apps/web/lib/api.ts`, `apps/web/app/history/page.tsx`, `apps/web/tests/history.analytics.test.tsx` |
| Ingestion catalog/provenance | Asset catalog + provenance generation exists | VERIFIED | `importers/reference_corpus_ingest.py`, `docs/guides/asset_catalog.json`, `docs/guides/provenance_index.json`, `apps/api/tests/test_reference_corpus_ingestion.py` |
| Workbook/PDF pairing | Pairing enforcement and dedup logic exists | VERIFIED | `importers/reference_corpus_ingest.py`, `apps/api/tests/test_reference_corpus_ingestion.py` |
| Full extraction quality | Guide artifacts contain extracted source text | NOT VERIFIED | `docs/guides/asset_catalog.json` shows `pdf_metadata_only`/`xlsx_metadata_only` with zero extracted chars |
| Video mapping quality | Broad exercise video coverage across templates | NOT VERIFIED | Most files in `programs/*.json` have near-zero `video.youtube_url` coverage |
| Canonical template quality | Imported templates are uniformly clean workout structures | NOT VERIFIED | Imported templates contain non-workout rows/sessions; example `programs/my_new_program_imported.json` |
| XLSX import sanitization | Structural/non-workout rows are filtered during import | VERIFIED | `importers/xlsx_to_program.py`, `apps/api/tests/test_xlsx_to_program_sanitization.py` |
| Ingestion quality report | Invalid sessions/missing prescription/missing video metrics are emitted | VERIFIED | `importers/ingestion_quality_report.py`, `scripts/generate_ingestion_quality_report.py`, `apps/api/tests/test_ingestion_quality_report.py`, `docs/validation/ingestion_quality_report.json`, `docs/validation/ingestion_quality_report.md` |
| Prior audit evidence paths | Referenced evidence files exist | NOT VERIFIED | Prior audit referenced programs/schema.py (file does not exist) |

## Audit Notes

- `docs/guides/generated/*.md` files exist, but many are metadata stubs with `(No text extracted)`.
- Runtime catalog currently includes high-session imported programs that likely represent workbook parsing noise, not true weekly structures.
- End-to-end coaching flow now includes user-visible recommendation timeline/rationale on `history`; ingestion quality remains the primary remaining gap.

## Immediate Corrective Actions

- Keep all future checkmarks gated by explicit test + artifact + file evidence.
- Validate evidence references automatically in preflight before implementation starts.
- Treat ingestion quality and template normalization as top-priority blockers before claiming coach-grade intelligence.

