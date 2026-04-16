from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BundleStatus = Literal["seed", "placeholder", "curated", "active", "deprecated"]
CurationStatus = Literal["seeded", "placeholder", "curated", "deprecated"]
ExerciseDemandLevel = Literal["low", "moderate", "high"] | None
ProgressionCompatibilityLevel = Literal["low", "moderate", "high"]


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value.strip() for value in values if value and value.strip()})


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


class ProvenanceRef(BaseModel):
    source_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    section_ref: str | None = None
    excerpt_hash: str | None = None
    confidence: float = Field(ge=0, le=1)
    curation_status: CurationStatus = "seeded"
    note: str | None = None


class SourceRegistryEntry(BaseModel):
    source_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(min_length=8)
    source_type: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    paired_source_ids: list[str] = Field(default_factory=list)
    program_family: str | None = None
    source_family_id: str | None = None
    split_scope: list[str] = Field(default_factory=list)
    bodypart_scope: list[str] = Field(default_factory=list)
    doctrine_modules: list[str] = Field(default_factory=list)
    extraction_capabilities: list[str] = Field(default_factory=list)
    authority_weight: float = Field(ge=0)
    classification_confidence: float = Field(ge=0, le=1)
    curation_status: CurationStatus = "seeded"
    derived_doc_paths: list[str] = Field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = Field(default_factory=list)

    @field_validator(
        "paired_source_ids",
        "split_scope",
        "bodypart_scope",
        "doctrine_modules",
        "extraction_capabilities",
        "derived_doc_paths",
    )
    @classmethod
    def validate_sorted_unique_lists(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)


class SourceRegistryBundle(BaseModel):
    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)
    aggregate_signature: str = Field(min_length=1)
    entries: list[SourceRegistryEntry] = Field(default_factory=list)

    @field_validator("entries")
    @classmethod
    def validate_unique_source_ids(cls, value: list[SourceRegistryEntry]) -> list[SourceRegistryEntry]:
        source_ids = [entry.source_id for entry in value]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("entries must have unique source_id values")
        return value


class ExerciseOverlapRelation(BaseModel):
    related_exercise_id: str = Field(min_length=1)
    relation: str = Field(min_length=1)


class CanonicalExerciseRecord(BaseModel):
    exercise_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    family_id: str = Field(min_length=1)
    movement_pattern: str | None = None
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    equipment_tags: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    technique_guidance: list[str] = Field(default_factory=list)
    progression_compatibility: list[ProgressionCompatibilityLevel] = Field(default_factory=list)
    substitution_class: str | None = None
    fatigue_cost: ExerciseDemandLevel = None
    skill_demand: ExerciseDemandLevel = None
    stability_demand: ExerciseDemandLevel = None
    overlap_relations: list[ExerciseOverlapRelation] = Field(default_factory=list)
    source_program_ids: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    curation_status: CurationStatus = "seeded"

    @field_validator(
        "aliases",
        "primary_muscles",
        "secondary_muscles",
        "equipment_tags",
        "contraindications",
        "technique_guidance",
        "progression_compatibility",
        "source_program_ids",
    )
    @classmethod
    def validate_sorted_unique_lists(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)


class ExerciseLibraryOverrideRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_id: str = Field(min_length=1)
    fatigue_cost: ExerciseDemandLevel = None
    skill_demand: ExerciseDemandLevel = None
    stability_demand: ExerciseDemandLevel = None
    progression_compatibility: list[ProgressionCompatibilityLevel] = Field(default_factory=list)

    @field_validator("progression_compatibility")
    @classmethod
    def validate_progression_compatibility(cls, value: list[ProgressionCompatibilityLevel]) -> list[ProgressionCompatibilityLevel]:
        normalized = _sorted_unique(value)
        if len(normalized) > 1:
            raise ValueError("progression_compatibility overrides may contain at most one value")
        return normalized


class ExerciseLibraryOverrideBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    records: list[ExerciseLibraryOverrideRecord] = Field(default_factory=list)

    @field_validator("records")
    @classmethod
    def validate_unique_override_exercise_ids(
        cls,
        value: list[ExerciseLibraryOverrideRecord],
    ) -> list[ExerciseLibraryOverrideRecord]:
        exercise_ids = [record.exercise_id for record in value]
        if len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError("exercise library override records must have unique exercise_id values")
        return value


class CanonicalExerciseLibraryBundle(BaseModel):
    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)
    aggregate_signature: str = Field(min_length=1)
    records: list[CanonicalExerciseRecord] = Field(default_factory=list)

    @field_validator("records")
    @classmethod
    def validate_unique_exercise_ids(cls, value: list[CanonicalExerciseRecord]) -> list[CanonicalExerciseRecord]:
        exercise_ids = [record.exercise_id for record in value]
        if len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError("records must have unique exercise_id values")
        return value


class DoctrineRuleStub(BaseModel):
    rule_id: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    description: str = Field(min_length=1)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def validate_tags_unique(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)


class DoctrineBundle(BaseModel):
    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    status: BundleStatus = "seed"
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)
    aggregate_signature: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)
    module_ids: list[str] = Field(default_factory=list)
    rules_by_module: dict[str, list[DoctrineRuleStub]] = Field(default_factory=dict)

    @field_validator("source_ids", "module_ids")
    @classmethod
    def validate_sorted_unique_lists(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)

    @model_validator(mode="after")
    def validate_rules_align_to_modules(self) -> "DoctrineBundle":
        declared_modules = set(self.module_ids)
        actual_modules = set(self.rules_by_module.keys())
        if actual_modules - declared_modules:
            raise ValueError("rules_by_module contains undeclared module ids")
        for module_id, rules in self.rules_by_module.items():
            for rule in rules:
                if rule.module_id != module_id:
                    raise ValueError("rule.module_id must match rules_by_module key")
        return self


class HardConstraint(BaseModel):
    constraint_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class SoftPreference(BaseModel):
    preference_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    default_weight: float = Field(ge=0)
    rationale: str = Field(min_length=1)


class ConstraintResolutionPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    resolution_order: list[str] = Field(default_factory=list)
    same_tier_tiebreaker: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("resolution_order")
    @classmethod
    def validate_resolution_order(cls, value: list[str]) -> list[str]:
        return _unique_preserve_order(value)


class MinimumViableProgramPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    minimum_sessions_per_week: int = Field(ge=1)
    minimum_exercises_per_session: int = Field(ge=1)
    fallback_order: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @field_validator("fallback_order")
    @classmethod
    def validate_fallback_order(cls, value: list[str]) -> list[str]:
        return _unique_preserve_order(value)


class AntiOveradaptationPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    observation_window_days: int = Field(ge=1)
    major_change_cooldown_days: int = Field(ge=0)
    max_major_changes_per_mesocycle: int = Field(ge=1)
    rationale: str = Field(min_length=1)


class DataSufficiencyPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    minimum_logged_sessions_for_major_change: int = Field(ge=0)
    minimum_checkins_for_split_change: int = Field(ge=0)
    minimum_exposures_for_major_exercise_rotation: int = Field(ge=0)
    safety_override_allowed: bool = True
    rationale: str = Field(min_length=1)


class GeneratedFullBodyAdaptiveLoopPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    program_scope: list[str] = Field(default_factory=list)
    explicit_review_precedence: bool = True
    require_generated_constructor_output: bool = True
    max_primary_axes_per_week: int = Field(ge=1)
    minimum_axis_persistence_weeks: int = Field(ge=1)
    minimum_prior_generated_weeks: int = Field(ge=0)
    minimum_logged_sessions_for_auto_adjustment: int = Field(ge=0)
    safety_override_allowed: bool = True
    load_adjustment_requires_exact_exercise_match: bool = True
    minimum_exact_match_exposures_for_load_adjustment: int = Field(ge=1)
    max_volume_targets_per_week: int = Field(ge=1)
    max_load_targets_per_week: int = Field(ge=1)
    volume_increase_set_delta: int = Field(ge=0)
    volume_decrease_set_delta: int = Field(le=0)
    load_increase_scale: float = Field(gt=0)
    load_decrease_scale: float = Field(gt=0)
    weak_point_set_delta: int = Field(ge=0)
    weak_point_max_boosted_exercises: int = Field(ge=1)
    rationale: str = Field(min_length=1)

    @field_validator("program_scope")
    @classmethod
    def validate_program_scope(cls, value: list[str]) -> list[str]:
        return _unique_preserve_order(value)


class GeneratedFullBodyBlockReviewPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    status: BundleStatus = "seed"
    program_scope: list[str] = Field(default_factory=list)
    explicit_review_precedence: bool = True
    require_generated_constructor_output: bool = True
    minimum_generated_weeks_for_block_review: int = Field(ge=0)
    minimum_review_window_weeks: int = Field(ge=1)
    stalled_block_underperformance_threshold: int = Field(ge=1)
    fatigued_block_recovery_threshold: int = Field(ge=1)
    continue_block_conservative_restrict_up_axes: list[str] = Field(default_factory=list)
    recovery_pivot_restricted_axes: list[str] = Field(default_factory=list)
    block_reset_resets_adaptive_persistence: bool = True
    rationale: str = Field(min_length=1)

    @field_validator("program_scope")
    @classmethod
    def validate_program_scope(cls, value: list[str]) -> list[str]:
        return _unique_preserve_order(value)

    @field_validator("continue_block_conservative_restrict_up_axes", "recovery_pivot_restricted_axes")
    @classmethod
    def validate_axis_tokens(cls, value: list[str]) -> list[str]:
        return _unique_preserve_order(value)


class PolicyBundle(BaseModel):
    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    status: BundleStatus = "seed"
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)
    aggregate_signature: str = Field(min_length=1)
    hard_constraints: list[HardConstraint] = Field(default_factory=list)
    soft_preferences: list[SoftPreference] = Field(default_factory=list)
    constraint_resolution_policy: ConstraintResolutionPolicy
    minimum_viable_program_policy: MinimumViableProgramPolicy
    anti_overadaptation_policy: AntiOveradaptationPolicy
    data_sufficiency_policy: DataSufficiencyPolicy
    generated_full_body_adaptive_loop_policy: GeneratedFullBodyAdaptiveLoopPolicy | None = None
    generated_full_body_block_review_policy: GeneratedFullBodyBlockReviewPolicy | None = None

    @field_validator("hard_constraints")
    @classmethod
    def validate_unique_hard_constraints(cls, value: list[HardConstraint]) -> list[HardConstraint]:
        constraint_ids = [item.constraint_id for item in value]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("hard_constraints must have unique constraint_id values")
        return value

    @field_validator("soft_preferences")
    @classmethod
    def validate_unique_soft_preferences(cls, value: list[SoftPreference]) -> list[SoftPreference]:
        preference_ids = [item.preference_id for item in value]
        if len(preference_ids) != len(set(preference_ids)):
            raise ValueError("soft_preferences must have unique preference_id values")
        return value


class CompiledArtifactManifestEntry(BaseModel):
    artifact_id: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    path: str = Field(min_length=1)
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)


class CompiledKnowledgeManifest(BaseModel):
    schema_version: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    input_signature: str = Field(min_length=1)
    output_signature: str = Field(min_length=1)
    aggregate_signature: str = Field(min_length=1)
    artifacts: list[CompiledArtifactManifestEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("artifacts")
    @classmethod
    def validate_unique_artifact_ids(cls, value: list[CompiledArtifactManifestEntry]) -> list[CompiledArtifactManifestEntry]:
        artifact_ids = [item.artifact_id for item in value]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("artifacts must have unique artifact_id values")
        return value

    @field_validator("warnings")
    @classmethod
    def validate_warnings_unique(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)
