from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class RepTarget(BaseModel):
    min: int = Field(ge=1)
    max: int = Field(ge=1)

    @field_validator("max")
    @classmethod
    def validate_max_at_least_min(cls, value: int, info: ValidationInfo) -> int:
        min_value = info.data.get("min")
        if isinstance(min_value, int) and value < min_value:
            raise ValueError("rep_target.max must be >= rep_target.min")
        return value


class WarmupStep(BaseModel):
    percent: int = Field(ge=1, le=100)
    reps: int = Field(ge=1)


class WorkSetPrescription(BaseModel):
    set_type: str
    sets: int = Field(ge=1)
    rep_target: RepTarget
    rir_target: int = Field(ge=0, le=6)


class AdaptiveSlot(BaseModel):
    slot_id: str = Field(min_length=1)
    order_index: int = Field(ge=1)
    exercise_id: str = Field(min_length=1)
    video_url: str | None = None
    warmup_prescription: list[WarmupStep] = Field(default_factory=list)
    work_sets: list[WorkSetPrescription] = Field(default_factory=list)
    notes: str | None = None


class AdaptiveDay(BaseModel):
    day_id: str = Field(min_length=1)
    day_name: str = Field(min_length=1)
    slots: list[AdaptiveSlot] = Field(default_factory=list)


class AdaptiveWeek(BaseModel):
    week_index: int = Field(ge=1)
    days: list[AdaptiveDay] = Field(default_factory=list)


class AdaptivePhase(BaseModel):
    phase_id: str = Field(min_length=1)
    phase_name: str = Field(min_length=1)
    weeks: list[AdaptiveWeek] = Field(default_factory=list)


class AdaptiveGoldProgramTemplate(BaseModel):
    program_id: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    source_workbook: str = Field(min_length=1)
    version: str = Field(min_length=1)
    split: str = Field(min_length=1)
    phases: list[AdaptivePhase] = Field(default_factory=list)


class StartingLoadRules(BaseModel):
    method: str = Field(min_length=1)
    default_rir_target: int = Field(ge=0, le=6)
    fallback_percent_estimated_1rm: int = Field(ge=1, le=100)


class ProgressionDecision(BaseModel):
    action: str = Field(min_length=1)
    percent: float | None = Field(default=None, gt=0)
    reduce_percent: float | None = Field(default=None, gt=0)
    after_exposures: int | None = Field(default=None, ge=1)


class ProgressionRules(BaseModel):
    success_condition: str = Field(min_length=1)
    on_success: ProgressionDecision
    on_in_range: ProgressionDecision
    on_under_target: ProgressionDecision


class FatigueTrigger(BaseModel):
    conditions: list[str] = Field(default_factory=list)


class FatigueAction(BaseModel):
    action: str = Field(min_length=1)
    set_delta: int


class FatigueRules(BaseModel):
    high_fatigue_trigger: FatigueTrigger
    on_high_fatigue: FatigueAction


class DeloadAction(BaseModel):
    set_reduction_percent: int = Field(ge=0, le=100)
    load_reduction_percent: int = Field(ge=0, le=100)


class DeloadRules(BaseModel):
    scheduled_every_n_weeks: int = Field(ge=1)
    early_deload_trigger: str = Field(min_length=1)
    on_deload: DeloadAction


class SubstitutionRules(BaseModel):
    equipment_mismatch: str = Field(min_length=1)
    repeat_failure_trigger: str = Field(min_length=1)


class AdaptiveGoldRuleSet(BaseModel):
    rule_set_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    program_scope: list[str] = Field(default_factory=list)
    source_pdf: str = Field(min_length=1)
    starting_load_rules: StartingLoadRules
    progression_rules: ProgressionRules
    fatigue_rules: FatigueRules
    deload_rules: DeloadRules
    substitution_rules: SubstitutionRules
    rationale_templates: dict[str, str] = Field(default_factory=dict)


class ExerciseAlternative(BaseModel):
    exercise_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    equipment_tags: list[str] = Field(default_factory=list)


class ExerciseKnowledgeEntry(BaseModel):
    exercise_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    execution: str = Field(min_length=1)
    coaching_cues: list[str] = Field(default_factory=list)
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    equipment_tags: list[str] = Field(default_factory=list)
    movement_pattern: str = Field(min_length=1)
    valid_substitutions: list[ExerciseAlternative] = Field(default_factory=list)
    default_video_url: str | None = None
    slot_usage_rationale: str = Field(min_length=1)


class ProgramIntent(BaseModel):
    program_id: str = Field(min_length=1)
    phase_goal: str = Field(min_length=1)
    progression_philosophy: str = Field(min_length=1)
    fatigue_management: str = Field(min_length=1)
    non_negotiables: list[str] = Field(default_factory=list)
    flexible_elements: list[str] = Field(default_factory=list)
    preserve_when_frequency_reduced: list[str] = Field(default_factory=list)


class CoverageTarget(BaseModel):
    muscle_group: str = Field(min_length=1)
    minimum_weekly_slots: int = Field(ge=1)


class FrequencyAdaptationRules(BaseModel):
    default_training_days: int = Field(ge=2, le=7)
    minimum_temporary_days: int = Field(ge=2, le=7)
    max_temporary_weeks: int = Field(ge=1, le=8)
    preserve_slot_roles: list[str] = Field(default_factory=list)
    reduce_slot_roles_first: list[str] = Field(default_factory=list)
    weak_area_bonus_slots: int = Field(ge=0, le=4)
    daily_slot_cap_when_compressed: int = Field(ge=3, le=12)
    coverage_targets: list[CoverageTarget] = Field(default_factory=list)
    reintegration_policy: str = Field(min_length=1)


class UserWeakAreaConstraint(BaseModel):
    muscle_group: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)
    desired_extra_slots_per_week: int = Field(ge=0, le=4)


class UserOverlayConstraints(BaseModel):
    available_training_days: int = Field(ge=2, le=7)
    temporary_duration_weeks: int = Field(ge=1, le=8)
    weak_areas: list[UserWeakAreaConstraint] = Field(default_factory=list)
    equipment_limits: list[str] = Field(default_factory=list)
    recovery_state: Literal["low", "normal", "high_fatigue"] = "normal"
    current_week_index: int = Field(ge=1)


class BlueprintWarmupStep(BaseModel):
    percent: int = Field(ge=1, le=100)
    reps: int = Field(ge=1)


class BlueprintWorkSet(BaseModel):
    set_type: Literal["work", "top", "backoff"] = "work"
    sets: int = Field(ge=1)
    rep_target: RepTarget
    rir_target: int | None = Field(default=None, ge=0, le=6)
    rpe_target: float | None = Field(default=None, ge=1, le=10)


class ProgramBlueprintSlot(BaseModel):
    slot_id: str = Field(min_length=1)
    order_index: int = Field(ge=1)
    exercise_id: str = Field(min_length=1)
    slot_role: Literal["primary_compound", "secondary_compound", "accessory", "isolation", "weak_point"]
    primary_muscles: list[str] = Field(default_factory=list)
    video_url: str | None = None
    warmup_prescription: list[BlueprintWarmupStep] = Field(default_factory=list)
    work_sets: list[BlueprintWorkSet] = Field(default_factory=list)
    notes: str | None = None


class ProgramBlueprintDay(BaseModel):
    day_id: str = Field(min_length=1)
    day_name: str = Field(min_length=1)
    slots: list[ProgramBlueprintSlot] = Field(default_factory=list)


class ProgramBlueprintWeekTemplate(BaseModel):
    week_template_id: str = Field(min_length=1)
    days: list[ProgramBlueprintDay] = Field(default_factory=list)


class ProgramBlueprint(BaseModel):
    program_id: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    source_workbook: str = Field(min_length=1)
    split: Literal["full_body", "upper_lower", "ppl"]
    default_training_days: int = Field(ge=2, le=7)
    total_weeks: int = Field(ge=1, le=24)
    week_sequence: list[str] = Field(default_factory=list)
    week_templates: list[ProgramBlueprintWeekTemplate] = Field(default_factory=list)

    @field_validator("week_sequence")
    @classmethod
    def validate_week_sequence(cls, value: list[str], info: ValidationInfo) -> list[str]:
        total_weeks = info.data.get("total_weeks")
        if isinstance(total_weeks, int) and len(value) != total_weeks:
            raise ValueError("week_sequence length must match total_weeks")
        return value


class ProgramOnboardingPackage(BaseModel):
    program_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_pdf: str = Field(min_length=1)
    blueprint: ProgramBlueprint
    exercise_library: list[ExerciseKnowledgeEntry] = Field(default_factory=list)
    program_intent: ProgramIntent
    frequency_adaptation_rules: FrequencyAdaptationRules


class AdaptationDecision(BaseModel):
    action: Literal["preserve", "combine", "rotate", "reduce"]
    exercise_id: str = Field(min_length=1)
    source_day_id: str = Field(min_length=1)
    target_day_id: str | None = None
    reason: str = Field(min_length=1)


class AdaptedDayPlan(BaseModel):
    day_id: str = Field(min_length=1)
    source_day_ids: list[str] = Field(default_factory=list)
    exercise_ids: list[str] = Field(default_factory=list)


class FrequencyAdaptationWeekResult(BaseModel):
    week_index: int = Field(ge=1)
    adapted_training_days: int = Field(ge=2, le=7)
    adapted_days: list[AdaptedDayPlan] = Field(default_factory=list)
    decisions: list[AdaptationDecision] = Field(default_factory=list)
    coverage_before: dict[str, int] = Field(default_factory=dict)
    coverage_after: dict[str, int] = Field(default_factory=dict)
    rationale: str = Field(min_length=1)


class FrequencyAdaptationResult(BaseModel):
    program_id: str = Field(min_length=1)
    from_days: int = Field(ge=2, le=7)
    to_days: int = Field(ge=2, le=7)
    duration_weeks: int = Field(ge=1, le=8)
    weak_areas: list[str] = Field(default_factory=list)
    weeks: list[FrequencyAdaptationWeekResult] = Field(default_factory=list)
    rejoin_policy: str = Field(min_length=1)
