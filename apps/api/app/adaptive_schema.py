from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


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
    rest_seconds: int | None = Field(default=None, ge=0)


class WorkSetPrescription(BaseModel):
    set_type: Literal["work", "top", "backoff"] = "work"
    sets: int = Field(ge=1)
    rep_target: RepTarget
    rir_target: int | None = Field(default=None, ge=0, le=6)
    rpe_target: float | None = Field(default=None, ge=1, le=10)
    load_target: str | None = None


class AdaptiveSlot(BaseModel):
    slot_id: str = Field(min_length=1)
    order_index: int = Field(ge=1)
    exercise_id: str = Field(min_length=1)
    slot_role: str | None = None
    video_url: str | None = None
    warmup_prescription: list[WarmupStep] = Field(default_factory=list)
    work_sets: list[WorkSetPrescription] = Field(default_factory=list)
    notes: str | None = None


class AdaptiveDay(BaseModel):
    day_id: str = Field(min_length=1)
    day_name: str = Field(min_length=1)
    day_role: str | None = None
    slots: list[AdaptiveSlot] = Field(default_factory=list)

    @field_validator("slots")
    @classmethod
    def validate_slots_unique_ids_and_order(cls, value: list[AdaptiveSlot]) -> list[AdaptiveSlot]:
        slot_ids = [slot.slot_id for slot in value]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slots must have unique slot_id values per day")

        order_indices = [slot.order_index for slot in value]
        if len(order_indices) != len(set(order_indices)):
            raise ValueError("slots must have unique order_index values per day")

        return value


class AdaptiveWeek(BaseModel):
    week_index: int = Field(ge=1)
    week_role: str | None = None
    days: list[AdaptiveDay] = Field(default_factory=list)

    @field_validator("days")
    @classmethod
    def validate_days_unique_ids(cls, value: list[AdaptiveDay]) -> list[AdaptiveDay]:
        day_ids = [day.day_id for day in value]
        if len(day_ids) != len(set(day_ids)):
            raise ValueError("days must have unique day_id values per week")
        return value


class AdaptivePhase(BaseModel):
    phase_id: str = Field(min_length=1)
    phase_name: str = Field(min_length=1)
    weeks: list[AdaptiveWeek] = Field(default_factory=list)

    @field_validator("weeks")
    @classmethod
    def validate_weeks_unique_indexes(cls, value: list[AdaptiveWeek]) -> list[AdaptiveWeek]:
        week_indexes = [week.week_index for week in value]
        if len(week_indexes) != len(set(week_indexes)):
            raise ValueError("weeks must have unique week_index values per phase")
        return value


class AdaptiveGoldProgramTemplate(BaseModel):
    program_id: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    source_workbook: str = Field(min_length=1)
    version: str = Field(min_length=1)
    split: str = Field(min_length=1)
    phases: list[AdaptivePhase] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_phases_unique_ids(self) -> "AdaptiveGoldProgramTemplate":
        if not self.phases:
            raise ValueError("phases must not be empty")

        phase_ids = [phase.phase_id for phase in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("phases must have unique phase_id values")
        return self


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


class SchedulerSorenessDeloadTrigger(BaseModel):
    minimum_severe_count: int = Field(ge=1)
    reason: str = Field(min_length=1)


class SchedulerAdherenceDeloadTrigger(BaseModel):
    maximum_score: int = Field(ge=1, le=5)
    reason: str = Field(min_length=1)


class SchedulerStimulusFatigueDeloadTrigger(BaseModel):
    deload_pressure: str = Field(min_length=1)
    recoverability: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class SchedulerMesocycleRules(BaseModel):
    sequence_completion_phase_transition_reason: str = Field(min_length=1)
    post_authored_sequence_behavior: str = Field(min_length=1)
    soreness_deload_trigger: SchedulerSorenessDeloadTrigger | None = None
    adherence_deload_trigger: SchedulerAdherenceDeloadTrigger | None = None
    stimulus_fatigue_deload_trigger: SchedulerStimulusFatigueDeloadTrigger | None = None


class SchedulerExerciseAdjustmentConditions(BaseModel):
    minimum_fatigue_score: float | None = Field(default=None, ge=0, le=1)
    minimum_consecutive_under_target_exposures: int | None = Field(default=None, ge=1)
    last_progression_actions: list[str] = Field(default_factory=list)


class SchedulerExerciseAdjustmentAction(BaseModel):
    load_scale: float = Field(gt=0)
    set_delta: int
    substitution_pressure: str = Field(min_length=1)
    substitution_guidance: str | None = None


class SchedulerExerciseAdjustmentPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    match_policy: Literal["all", "any"] = "all"
    conditions: SchedulerExerciseAdjustmentConditions
    adjustment: SchedulerExerciseAdjustmentAction


class SchedulerExerciseAdjustmentRules(BaseModel):
    policies: list[SchedulerExerciseAdjustmentPolicy] = Field(default_factory=list)
    default_adjustment: SchedulerExerciseAdjustmentAction
    substitution_pressure_guidance: dict[str, str | None] = Field(default_factory=dict)


class SchedulerSessionSelectionRules(BaseModel):
    recent_history_exercise_limit: int = Field(ge=1, le=12)
    anchor_first_session_when_day_roles_present: bool = False
    required_day_roles_when_compressed: list[str] = Field(default_factory=list)
    structural_slot_role_priority: dict[str, int] = Field(default_factory=dict)
    day_role_priority: dict[str, int] = Field(default_factory=dict)
    missed_day_policy: str = Field(min_length=1)


class SchedulerTimeBudgetThreshold(BaseModel):
    maximum_minutes: int = Field(ge=1)
    exercise_limit: int = Field(ge=1)


class SchedulerSessionExerciseCapRules(BaseModel):
    time_budget_thresholds: list[SchedulerTimeBudgetThreshold] = Field(default_factory=list)
    default_slot_role_priority: dict[str, int] = Field(default_factory=dict)
    day_role_slot_role_priority_overrides: dict[str, dict[str, int]] = Field(default_factory=dict)


class SchedulerMuscleCoverageRules(BaseModel):
    tracked_muscles: list[str] = Field(default_factory=list)
    minimum_sets_per_muscle: int = Field(ge=0)
    authored_label_normalization: dict[str, str] = Field(default_factory=dict)


class GeneratedWeekSchedulerRules(BaseModel):
    mesocycle: SchedulerMesocycleRules
    exercise_adjustment: SchedulerExerciseAdjustmentRules
    session_selection: SchedulerSessionSelectionRules
    session_exercise_cap: SchedulerSessionExerciseCapRules
    muscle_coverage: SchedulerMuscleCoverageRules


class RuleSourceSection(BaseModel):
    field: str = Field(min_length=1)
    source_doc: str = Field(min_length=1)
    source_pdf: str = Field(min_length=1)
    heading: str | None = None
    excerpt: str = Field(min_length=1)


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
    generated_week_scheduler_rules: GeneratedWeekSchedulerRules | None = None
    rationale_templates: dict[str, str] = Field(default_factory=dict)
    source_sections: list[RuleSourceSection] = Field(default_factory=list)

    @field_validator("program_scope")
    @classmethod
    def validate_program_scope_non_empty_and_unique(cls, value: list[str]) -> list[str]:
        normalized = [item for item in value if item]
        if not normalized:
            raise ValueError("program_scope must contain at least one program_id")
        if len(normalized) != len(set(normalized)):
            raise ValueError("program_scope must not contain duplicate program_id values")
        return normalized


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


class UserProgramState(BaseModel):
    program_id: str = Field(min_length=1)
    phase_id: str = Field(min_length=1)
    week_index: int = Field(ge=1)
    day_id: str | None = None
    session_id: str | None = None
    last_generated_week_start: date | None = None


class ExercisePerformanceEntry(BaseModel):
    exercise_id: str = Field(min_length=1)
    performed_at: datetime
    set_index: int = Field(ge=1)
    reps: int = Field(ge=1)
    weight: float = Field(ge=0)
    rpe: float | None = Field(default=None, ge=1, le=10)


class ProgressionStateEntry(BaseModel):
    exercise_id: str = Field(min_length=1)
    current_working_weight: float = Field(ge=0)
    exposure_count: int = Field(ge=0)
    consecutive_under_target_exposures: int = Field(ge=0)
    last_progression_action: str = Field(min_length=1)
    last_updated_at: datetime | None = None


class FatigueState(BaseModel):
    recovery_state: Literal["low", "normal", "high_fatigue"] = "normal"
    severe_soreness_count: int = Field(ge=0)
    session_rpe_avg: float | None = Field(default=None, ge=1, le=10)
    soreness_by_muscle: dict[str, Literal["none", "mild", "moderate", "severe"]] = Field(default_factory=dict)
    flagged_muscles: list[str] = Field(default_factory=list)


class AdherenceState(BaseModel):
    latest_adherence_score: int = Field(ge=1, le=5)
    rolling_average_score: float | None = Field(default=None, ge=1, le=5)
    missed_session_count: int = Field(ge=0)


class ReadinessState(BaseModel):
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    pain_flags: list[str] = Field(default_factory=list)
    recovery_risk_flags: list[str] = Field(default_factory=list)


class ConstraintState(BaseModel):
    days_available: int | None = Field(default=None, ge=2, le=5)
    split_preference: str | None = None
    training_location: str | None = None
    equipment_profile: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    nutrition_phase: str | None = None
    session_time_budget_minutes: int | None = Field(default=None, ge=15, le=240)
    movement_restrictions: list[str] = Field(default_factory=list)
    near_failure_tolerance: Literal["low", "moderate", "high"] | None = None


class StallState(BaseModel):
    stalled_exercise_ids: list[str] = Field(default_factory=list)
    consecutive_underperformance_weeks: int = Field(ge=0)
    phase_stagnation_weeks: int = Field(ge=0)


class LatestMesocycleState(BaseModel):
    week_index: int | None = Field(default=None, ge=1)
    trigger_weeks_effective: int | None = Field(default=None, ge=1)
    authored_week_index: int | None = Field(default=None, ge=1)
    authored_week_role: str | None = None
    authored_sequence_length: int | None = Field(default=None, ge=1)
    authored_sequence_complete: bool = False
    phase_transition_pending: bool = False
    phase_transition_reason: str | None = None
    post_authored_behavior: str | None = None


class CoachingState(BaseModel):
    readiness: ReadinessState = Field(default_factory=ReadinessState)
    fatigue: FatigueState
    adherence: AdherenceState
    stall: StallState
    mesocycle: LatestMesocycleState = Field(default_factory=LatestMesocycleState)


class GenerationState(BaseModel):
    prior_generated_weeks_by_program: dict[str, int] = Field(default_factory=dict)
    under_target_muscles: list[str] = Field(default_factory=list)
    mesocycle_trigger_weeks_effective: int | None = Field(default=None, ge=1)
    latest_mesocycle: LatestMesocycleState = Field(default_factory=LatestMesocycleState)

    @field_validator("prior_generated_weeks_by_program")
    @classmethod
    def validate_non_negative_generated_week_counts(cls, value: dict[str, int]) -> dict[str, int]:
        for program_id, count in value.items():
            if count < 0:
                raise ValueError(f"prior_generated_weeks_by_program[{program_id}] must be non-negative")
        return value


class UserTrainingState(BaseModel):
    user_program_state: UserProgramState
    exercise_performance_history: list[ExercisePerformanceEntry] = Field(default_factory=list)
    progression_state_per_exercise: list[ProgressionStateEntry] = Field(default_factory=list)
    fatigue_state: FatigueState
    adherence_state: AdherenceState
    readiness_state: ReadinessState = Field(default_factory=ReadinessState)
    coaching_state: CoachingState = Field(
        description="Canonical coaching decision state used by preview and coaching runtime surfaces."
    )
    constraint_state: ConstraintState
    stall_state: StallState
    generation_state: GenerationState = Field(default_factory=GenerationState)

    @field_validator("progression_state_per_exercise")
    @classmethod
    def validate_unique_progression_state_exercise_ids(
        cls,
        value: list[ProgressionStateEntry],
    ) -> list[ProgressionStateEntry]:
        exercise_ids = [entry.exercise_id for entry in value]
        if len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError("progression_state_per_exercise must have unique exercise_id values")
        return value


class BlueprintWarmupStep(BaseModel):
    percent: int = Field(ge=1, le=100)
    reps: int = Field(ge=1)


class BlueprintWorkSet(BaseModel):
    set_type: Literal["work", "top", "backoff"] = "work"
    sets: int = Field(ge=1)
    rep_target: RepTarget
    rir_target: int | None = Field(default=None, ge=0, le=6)
    rpe_target: float | None = Field(default=None, ge=1, le=10)
    load_target: str | None = None


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
    day_role: str | None = None
    slots: list[ProgramBlueprintSlot] = Field(default_factory=list)

    @field_validator("slots")
    @classmethod
    def validate_slots_unique_ids_and_order(cls, value: list[ProgramBlueprintSlot]) -> list[ProgramBlueprintSlot]:
        slot_ids = [slot.slot_id for slot in value]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slots must have unique slot_id values per day")

        order_indices = [slot.order_index for slot in value]
        if len(order_indices) != len(set(order_indices)):
            raise ValueError("slots must have unique order_index values per day")

        return value


class ProgramBlueprintWeekTemplate(BaseModel):
    week_template_id: str = Field(min_length=1)
    days: list[ProgramBlueprintDay] = Field(default_factory=list)

    @field_validator("days")
    @classmethod
    def validate_days_unique_ids(cls, value: list[ProgramBlueprintDay]) -> list[ProgramBlueprintDay]:
        day_ids = [day.day_id for day in value]
        if len(day_ids) != len(set(day_ids)):
            raise ValueError("days must have unique day_id values per week_template")
        return value


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

    @model_validator(mode="after")
    def validate_week_templates_cover_sequence(self) -> "ProgramBlueprint":
        if not self.week_templates:
            raise ValueError("week_templates must not be empty")

        template_ids = [template.week_template_id for template in self.week_templates]
        if len(template_ids) != len(set(template_ids)):
            raise ValueError("week_templates must have unique week_template_id values")

        template_id_set = set(template_ids)
        missing = [template_id for template_id in self.week_sequence if template_id not in template_id_set]
        if missing:
            raise ValueError(f"week_sequence references unknown week_template_id values: {', '.join(sorted(set(missing)))}")

        return self


class ProgramOnboardingPackage(BaseModel):
    program_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_pdf: str = Field(min_length=1)
    blueprint: ProgramBlueprint
    exercise_library: list[ExerciseKnowledgeEntry] = Field(default_factory=list)
    program_intent: ProgramIntent
    frequency_adaptation_rules: FrequencyAdaptationRules

    @model_validator(mode="after")
    def validate_program_id_alignment(self) -> "ProgramOnboardingPackage":
        if self.program_id != self.blueprint.program_id:
            raise ValueError("program_id must match blueprint.program_id")
        if self.program_id != self.program_intent.program_id:
            raise ValueError("program_id must match program_intent.program_id")
        return self


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
    decision_trace: dict[str, Any]
