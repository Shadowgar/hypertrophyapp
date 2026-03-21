from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AssessmentSourceType = Literal["profile", "training_state", "system_default"]
AssessmentRuleSourceType = Literal["doctrine", "policy", "system_default"]
ExperienceLevel = Literal["novice", "early_intermediate", "advanced"]
RecoveryProfile = Literal["normal", "low_recovery"]
ScheduleProfile = Literal["normal", "low_time", "inconsistent_schedule"]
EquipmentContext = Literal["full_gym", "restricted_equipment"]
FatigueToleranceProfile = Literal["low", "moderate", "high"]
WeakPointSource = Literal["explicit", "inferred"]


class ProfileAssessmentInput(BaseModel):
    days_available: int = Field(ge=2, le=5)
    split_preference: str | None = None
    training_location: str | None = None
    equipment_profile: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    session_time_budget_minutes: int | None = Field(default=None, ge=15, le=240)
    movement_restrictions: list[str] = Field(default_factory=list)
    near_failure_tolerance: FatigueToleranceProfile | None = None


class AssessmentTraceRef(BaseModel):
    source_type: AssessmentSourceType
    source_path: str = Field(min_length=1)
    source_id: str = Field(min_length=1)


class AssessmentRuleSource(BaseModel):
    source_type: AssessmentRuleSourceType
    source_id: str = Field(min_length=1)
    note: str | None = None


class AssessmentFieldTrace(BaseModel):
    input_refs: list[AssessmentTraceRef] = Field(default_factory=list)
    rule_sources: list[AssessmentRuleSource] = Field(default_factory=list)


class WeakPointPriority(BaseModel):
    muscle_group: str = Field(min_length=1)
    priority_rank: int = Field(ge=1)
    source: WeakPointSource
    trace: AssessmentFieldTrace


class BaselineSignalSummary(BaseModel):
    progression_exposure_total: int = Field(ge=0)
    tracked_progression_entries: int = Field(ge=0)
    performance_history_entries: int = Field(ge=0)
    under_target_muscle_count: int = Field(ge=0)
    prior_generated_week_total: int = Field(ge=0)
    available_equipment_tags: list[str] = Field(default_factory=list)


class UserAssessment(BaseModel):
    assessment_id: str = Field(min_length=1)
    experience_level: ExperienceLevel
    user_class_flags: list[str] = Field(default_factory=list)
    days_available: int = Field(ge=2, le=5)
    split_preference: str | None = None
    session_time_budget_minutes: int | None = Field(default=None, ge=15, le=240)
    recovery_profile: RecoveryProfile
    schedule_profile: ScheduleProfile
    equipment_context: EquipmentContext
    fatigue_tolerance_profile: FatigueToleranceProfile
    movement_restrictions: list[str] = Field(default_factory=list)
    weak_point_priorities: list[WeakPointPriority] = Field(default_factory=list)
    comeback_flag: bool = False
    prior_working_weight_by_exercise_id: dict[str, float] = Field(default_factory=dict)
    baseline_signal_summary: BaselineSignalSummary
    field_trace: dict[str, AssessmentFieldTrace] = Field(default_factory=dict)
    system_default_ids_used: list[str] = Field(default_factory=list)
