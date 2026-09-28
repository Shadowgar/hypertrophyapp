# Exercise catalog ownership

Target ownership under [source](../contracts/authored-source.md), [execution](../contracts/execution-plan.md) and [metadata accounting](../contracts/metadata-accounting.md); mechanisms Proposed. Audited implementation and freeze: [current state](current-state.md). Requirements: [AUTH-FID](../requirements/catalog.md#auth-fid), [GEN](../requirements/catalog.md#gen), [PERF](../requirements/catalog.md#perf).

Catalog identity describes an exercise/variant; it cannot replace source slot or scheduled occurrence identity. Preserve equipment, movement pattern, muscles, technique and source-approved substitution provenance. Repeated exercise names may represent distinct source slots. A performed substitution retains the source slot and confirmed variant; comparison cohorts must account for variant/equipment/technique and missing metadata.

Build/importers own source/catalog lineage; deterministic decision owners consume declared metadata. Accounting may describe planned/performed muscle dose with explicit conventions, missing-data coverage and denominator. It is not proof of muscle growth or permission to alter Authored prescriptions. Restriction/pain metadata is non-diagnostic.

The [historical metadata model](EXERCISE_METADATA_MODEL.md) retains future fit, fatigue, time, overlap, role, substitution and skill fields. Their presence does not activate scoring. Metadata-v2 scoring stays disabled/no-op; any reactivation is separately approved and verified. Future collision/substitution policies need negative Authored tests and coherent reporting, not silent generic filtering.
