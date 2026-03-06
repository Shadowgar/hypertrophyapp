# Master Plan Checkmark Audit - Adaptive Coaching Rebuild

Last audited: 2026-03-06

Status legend:
- VERIFIED
- PARTIAL
- NOT VERIFIED

## Verification Matrix

| Domain | Claim | Status | Evidence |
| --- | --- | --- | --- |
| Runtime source boundary | Runtime does not parse raw PDF/XLSX | VERIFIED | `apps/api/app/routers/*.py`, `importers/xlsx_to_program.py`, `importers/reference_corpus_ingest.py` |
| Runtime guide artifact coupling | API/web runtime does not read `docs/guides/*` artifacts | VERIFIED | `apps/api/app/routers/plan.py`, `apps/web/app/settings/page.tsx`, `apps/web/lib/api.ts` |
| Runtime template catalog hygiene | Runtime list excludes legacy imported artifacts | VERIFIED | `apps/api/app/program_loader.py`, `apps/api/tests/test_program_loader_dedup.py`, `programs/archive_imports/README.md` |
| Coaching timeline UX | User can view recommendation timeline with rationale | VERIFIED | `apps/web/app/history/page.tsx`, `apps/web/tests/history.analytics.test.tsx` |
| Onboarding failure transparency | Register/login/profile failures expose backend detail text | VERIFIED | `apps/web/app/onboarding/page.tsx`, `apps/web/tests/onboarding.error.test.tsx` |
| Ingestion quality report | Metrics for invalid sessions/missing fields are generated | VERIFIED | `importers/ingestion_quality_report.py`, `docs/validation/ingestion_quality_report.json` |
| Full extraction policy | CI/local ingestion mode policy is documented and scripted | PARTIAL | `docs/guides/FULL_EXTRACTION_RUNBOOK.md`, `scripts/reference_ingest.sh`, `scripts/verify_guides_checksums.py` |
| Full extraction artifact quality | All guides have non-empty extracted content | NOT VERIFIED | `scripts/reference_ingest.sh local-full` currently fails on `reference/My-Favorite-Exercise-for-Each-Body-Part.pdf` |
| Canonical schema completeness | Program/catalog/rules/user-state schemas are finalized and enforced | PARTIAL | `docs/Canonical_Program_Schema.md`, `docs/redesign/Adaptive_Coaching_Redesign.md`, `apps/api/app/adaptive_schema.py`, `apps/api/tests/test_adaptive_gold_schema_contract.py` |
| Gold sample baseline | One manually validated sample template + rules exists | PARTIAL | `programs/gold/adaptive_full_body_gold_v0_1.json`, `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json` |
| Adaptation preview API | Deterministic frequency adaptation supports 2/3/4/5 day targets | VERIFIED | `apps/api/app/routers/plan.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`, `packages/core-engine/tests/test_onboarding_adaptation.py` |
| Weak-area persistence | User weak areas are stored and returned via profile API | VERIFIED | `apps/api/app/models.py`, `apps/api/app/routers/profile.py`, `apps/api/alembic/versions/0010_user_weak_areas.py` |
| Decision engine v2 | Deterministic adaptation fully grounded in canonical rules layer | PARTIAL | Frequency adaptation path delivered; broader load/progression integration still pending |
| Library-wide migration | Remaining program library migrated to canonical v2 contracts | PARTIAL | Imported variants archived in `programs/archive_imports/`; full v2 migration of all templates still pending |

## Notes

- Current guide markdown output remains excerpt-oriented and provenance-focused.
- Redesign target requires moving coaching runtime dependence to canonical templates + typed rule objects.
- Architecture audit matrix published at `docs/redesign/Architecture_Audit_Matrix.md`.
