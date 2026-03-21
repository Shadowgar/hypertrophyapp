from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ComplexityCeiling = Literal["simple", "standard"]
VolumeTier = Literal["conservative", "moderate"]
PatternCoverageStatus = Literal["covered", "insufficient", "empty"]


class BlueprintTraceRef(BaseModel):
    doctrine_rule_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    exercise_ids: list[str] = Field(default_factory=list)
    system_default_ids: list[str] = Field(default_factory=list)


class MovementPatternRequirement(BaseModel):
    movement_pattern: str = Field(min_length=1)
    minimum_weekly_exposures: int = Field(ge=1)
    priority_rank: int = Field(ge=1)
    trace: BlueprintTraceRef


class MovementPatternCoverage(BaseModel):
    movement_pattern: str = Field(min_length=1)
    minimum_weekly_exposures: int = Field(ge=1)
    candidate_count: int = Field(ge=0)
    candidate_exercise_ids: list[str] = Field(default_factory=list)
    status: PatternCoverageStatus
    trace: BlueprintTraceRef


class PatternInsufficiencyRecord(BaseModel):
    movement_pattern: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    minimum_weekly_exposures: int = Field(ge=1)
    candidate_count: int = Field(ge=0)
    candidate_exercise_ids: list[str] = Field(default_factory=list)
    trace: BlueprintTraceRef


class GeneratedFullBodyBlueprintInput(BaseModel):
    blueprint_input_id: str = Field(min_length=1)
    target_split: Literal["full_body"] = "full_body"
    assessment_id: str = Field(min_length=1)
    doctrine_bundle_id: str = Field(min_length=1)
    policy_bundle_id: str = Field(min_length=1)
    exercise_library_bundle_id: str = Field(min_length=1)
    hard_constraint_ids: list[str] = Field(default_factory=list)
    soft_preference_weights: dict[str, float] = Field(default_factory=dict)
    session_count: int = Field(ge=2, le=5)
    session_exercise_cap: int = Field(ge=1)
    volume_tier: VolumeTier
    complexity_ceiling: ComplexityCeiling
    required_movement_patterns: list[MovementPatternRequirement] = Field(default_factory=list)
    candidate_exercise_ids_by_pattern: dict[str, list[str]] = Field(default_factory=dict)
    weak_point_candidate_exercise_ids_by_muscle: dict[str, list[str]] = Field(default_factory=dict)
    excluded_exercise_ids: list[str] = Field(default_factory=list)
    pattern_coverage: list[MovementPatternCoverage] = Field(default_factory=list)
    pattern_insufficiencies: list[PatternInsufficiencyRecord] = Field(default_factory=list)
    field_trace: dict[str, BlueprintTraceRef] = Field(default_factory=dict)
    system_default_ids_used: list[str] = Field(default_factory=list)
