# Legacy qualification evidence

Classified 2026-09-28; evidence retains its original date/revision/environment and original negative findings/open tasks. A missing environment/revision stays unknown. No current qualification or acceptance is inferred from old pass counts/checkmarks. Current procedure: [Authored qualification](../../quality/authored-qualification.md), [release gates](../../quality/release-gates.md), [evidence policy](../README.md).

| Retained evidence | Scope / limitation |
|---|---|
| [Phase 1 dogfood](phase1-dogfood.md) | Original simulated/manual claims and unresolved qualitative scope; not a new device run. |
| [Metadata handoff](metadata-handoff.md) | Original metadata evidence and limitations; scoring remains frozen. |
| [Phase 2 handoff](phase2-handoff.md) | Original claims/checks retained; later September audit established missing AMRAP source rows. |
| [Phase 2 parity matrix](../../validation/phase2_fullbody_parity_matrix.md) | Supporting original parity checks, not all-field/source completeness certification. |
| [Original dogfood run checklist](../../implementation/DOGFOOD_PHASE1_RUN_CHECKLIST.md) | Retained prompts/tasks, original results and unknown device scope. |
| [Metadata report](../../validation/exercise_metadata_quality_audit.md) / [JSON](../../validation/exercise_metadata_quality_audit.json) | Generator-owned outputs stay byte-identical at tool-consumed paths; no manual rewriting. |
| [Ingestion report](../../validation/ingestion_quality_report.md) / [JSON](../../validation/ingestion_quality_report.json) | Generated original ingestion/qualification scope; not proof all source prescriptions are admitted. |
| [Bundle metrics](../../validation/mobile_perf_metrics.md) / [JSON](../../validation/mobile_perf_metrics.json) | Static bundle evidence, not background/resume/accessibility or real-device performance qualification. |

Generators still write the six report files at their original paths. Their proposed relocations require separately authorized tooling changes; this migration supplies classification/navigation, not copies with misleading duplicate ownership. [September audit summary](../../audits/2026-09-28-codebase-product-documentation-audit.md) and [all-file registry](../../audits/2026-09-28-documentation-migration-registry.md) preserve later findings and original hashes.
