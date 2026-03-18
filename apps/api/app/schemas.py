from datetime import date, datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from .adaptive_schema import UserTrainingState


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class DevWipeUserRequest(BaseModel):
    email: EmailStr
    confirmation: str = Field(min_length=4)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PasswordResetRequestResponse(BaseModel):
    status: str
    reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8)


class StatusResponse(BaseModel):
    status: str


class WorkoutUndoLastSetRequest(BaseModel):
    exercise_id: str


class ProfileUpsert(BaseModel):
    name: str
    age: int
    weight: float
    gender: str
    split_preference: str
    selected_program_id: str | None = None
    training_location: str | None = None
    equipment_profile: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    onboarding_answers: dict[str, Any] = Field(default_factory=dict)
    days_available: int = Field(ge=2, le=5)
    session_time_budget_minutes: int | None = Field(default=None, ge=15, le=240)
    movement_restrictions: list[str] = Field(default_factory=list)
    near_failure_tolerance: Literal["low", "moderate", "high"] | None = None
    nutrition_phase: str
    calories: int
    protein: int
    fat: int
    carbs: int


class ProfileResponse(ProfileUpsert):
    email: EmailStr


class UserTrainingStateResponse(UserTrainingState):
    pass


class WeeklyCheckinRequest(BaseModel):
    week_start: date
    body_weight: float = Field(gt=0)
    adherence_score: int = Field(ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    pain_flags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("week_start")
    @classmethod
    def validate_week_start(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        if value > date.today():
            raise ValueError("week_start cannot be in the future")
        return value


class WeeklyExerciseFaultResponse(BaseModel):
    primary_exercise_id: str
    exercise_id: str
    name: str
    planned_sets: int
    completed_sets: int
    completion_pct: int
    target_reps_min: int
    target_reps_max: int
    average_performed_reps: float
    target_weight: float
    average_performed_weight: float
    guidance: str
    fault_score: int
    fault_level: str
    fault_reasons: list[str]


class WeeklyPerformanceSummaryResponse(BaseModel):
    previous_week_start: date
    previous_week_end: date
    planned_sets_total: int
    completed_sets_total: int
    completion_pct: int
    faulty_exercise_count: int
    exercise_faults: list[WeeklyExerciseFaultResponse]


class WeeklyReviewStatusResponse(BaseModel):
    today_is_sunday: bool
    review_required: bool
    current_week_start: date
    week_start: date
    previous_week_start: date
    previous_week_end: date
    existing_review_submitted: bool
    previous_week_summary: WeeklyPerformanceSummaryResponse | None = None


class WeeklyExerciseAdjustmentResponse(BaseModel):
    primary_exercise_id: str
    set_delta: int
    weight_scale: float
    rationale: str


class WeeklyPlanAdjustmentResponse(BaseModel):
    global_set_delta: int
    global_weight_scale: float
    weak_point_exercises: list[str]
    exercise_overrides: list[WeeklyExerciseAdjustmentResponse]


class WeeklyReviewSubmitRequest(BaseModel):
    body_weight: float = Field(gt=0)
    calories: int = Field(gt=0)
    protein: int = Field(gt=0)
    fat: int = Field(gt=0)
    carbs: int = Field(gt=0)
    adherence_score: int = Field(ge=1, le=5)
    sessions_next_week: int | None = Field(default=None, ge=2, le=5)
    notes: str | None = None
    nutrition_phase: str | None = None
    week_start: date | None = None

    @field_validator("week_start")
    @classmethod
    def validate_week_start_if_present(cls, value: date | None) -> date | None:
        if value is None:
            return value
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value


class WeeklyReviewSubmitResponse(BaseModel):
    status: str
    week_start: date
    previous_week_start: date
    readiness_score: int
    global_guidance: str
    fault_count: int
    summary: WeeklyPerformanceSummaryResponse
    adjustments: WeeklyPlanAdjustmentResponse
    decision_trace: dict[str, Any]


SorenessSeverity = Literal["none", "mild", "moderate", "severe"]


class SorenessEntryCreateRequest(BaseModel):
    entry_date: date
    severity_by_muscle: dict[str, SorenessSeverity] = Field(default_factory=dict)
    notes: str | None = None


class SorenessEntryResponse(BaseModel):
    id: str
    entry_date: date
    severity_by_muscle: dict[str, SorenessSeverity]
    notes: str | None = None
    created_at: datetime


class BodyMeasurementEntryCreateRequest(BaseModel):
    measured_on: date
    name: str = Field(min_length=1, max_length=80)
    value: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=16)


class BodyMeasurementEntryUpdateRequest(BaseModel):
    measured_on: date | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    value: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=16)


class BodyMeasurementEntryResponse(BaseModel):
    id: str
    measured_on: date
    name: str
    value: float
    unit: str
    created_at: datetime


class GenerateWeekPlanRequest(BaseModel):
    template_id: str | None = None


class FrequencyAdaptationPreviewRequest(BaseModel):
    program_id: str | None = None
    target_days: int = Field(ge=2, le=5)
    duration_weeks: int = Field(default=2, ge=1, le=4)
    weak_areas: list[str] = Field(default_factory=list)


class FrequencyAdaptationApplyRequest(BaseModel):
    program_id: str | None = None
    target_days: int = Field(ge=2, le=5)
    duration_weeks: int = Field(default=2, ge=1, le=8)
    weak_areas: list[str] = Field(default_factory=list)


class FrequencyAdaptationApplyResponse(BaseModel):
    status: str
    program_id: str
    target_days: int
    duration_weeks: int
    weeks_remaining: int
    weak_areas: list[str]
    decision_trace: dict[str, Any]


class ScheduleAdaptationPreviewResponse(BaseModel):
    from_days: int
    to_days: int
    kept_sessions: list[str]
    dropped_sessions: list[str]
    added_sessions: list[str]
    risk_level: Literal["low", "medium", "high"]
    muscle_set_delta: dict[str, int]
    tradeoffs: list[str]


class ProgressionDecisionResponse(BaseModel):
    action: Literal["progress", "hold", "deload"]
    load_scale: float
    set_delta: int
    reason: str
    rationale: str


class PhaseTransitionResponse(BaseModel):
    next_phase: Literal["accumulation", "intensification", "deload"]
    reason: str
    rationale: str
    authored_sequence_complete: bool = False
    transition_pending: bool = False
    recommended_action: str | None = None
    post_authored_behavior: str | None = None


class SpecializationPreviewResponse(BaseModel):
    focus_muscles: list[str]
    focus_adjustments: dict[str, int]
    donor_adjustments: dict[str, int]
    uncompensated_added_sets: int


class WarmupSampleResponse(BaseModel):
    exercise_id: str
    warmups: list[float]


class ProgramMediaWarmupSummaryResponse(BaseModel):
    total_exercises: int
    video_linked_exercises: int
    video_coverage_pct: float
    sample_warmups: list[WarmupSampleResponse]


class IntelligenceCoachPreviewRequest(BaseModel):
    template_id: str | None = None
    from_days: int = Field(ge=2, le=7)
    to_days: int = Field(ge=2, le=7)
    completion_pct: int = Field(default=90, ge=0, le=100)
    adherence_score: int = Field(default=3, ge=1, le=5)
    soreness_level: SorenessSeverity = "none"
    average_rpe: float | None = Field(default=None, ge=1.0, le=10.0)
    current_phase: Literal["accumulation", "intensification", "deload"] = "accumulation"
    weeks_in_phase: int = Field(default=1, ge=1, le=16)
    stagnation_weeks: int = Field(default=0, ge=0, le=8)
    readiness_score: int | None = Field(default=None, ge=0, le=100)
    lagging_muscles: list[str] = Field(default_factory=list)
    target_min_sets: int = Field(default=8, ge=4, le=20)


class IntelligenceCoachPreviewResponse(BaseModel):
    recommendation_id: str
    template_id: str
    program_name: str
    schedule: ScheduleAdaptationPreviewResponse
    progression: ProgressionDecisionResponse
    phase_transition: PhaseTransitionResponse
    specialization: SpecializationPreviewResponse
    media_warmups: ProgramMediaWarmupSummaryResponse
    decision_trace: dict[str, Any]


class ApplyPhaseDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1)
    confirm: bool = False


class ApplyPhaseDecisionResponse(BaseModel):
    status: str
    recommendation_id: str
    applied_recommendation_id: str | None = None
    requires_confirmation: bool
    applied: bool
    next_phase: Literal["accumulation", "intensification", "deload"]
    reason: str
    rationale: str
    decision_trace: dict[str, Any]


class ApplySpecializationDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1)
    confirm: bool = False


class ApplySpecializationDecisionResponse(BaseModel):
    status: str
    recommendation_id: str
    applied_recommendation_id: str | None = None
    requires_confirmation: bool
    applied: bool
    focus_muscles: list[str]
    focus_adjustments: dict[str, int]
    donor_adjustments: dict[str, int]
    uncompensated_added_sets: int
    decision_trace: dict[str, Any]


class CoachingRecommendationTimelineEntry(BaseModel):
    recommendation_id: str
    recommendation_type: str
    status: str
    template_id: str
    current_phase: str
    recommended_phase: str
    progression_action: str
    rationale: str
    focus_muscles: list[str]
    created_at: datetime
    applied_at: datetime | None = None


class CoachingRecommendationTimelineResponse(BaseModel):
    entries: list[CoachingRecommendationTimelineEntry]


class ProgramRecommendationResponse(BaseModel):
    current_program_id: str
    recommended_program_id: str
    reason: str
    rationale: str
    decision_trace: dict[str, Any]
    compatible_program_ids: list[str]
    generated_at: datetime


class ProgramSwitchRequest(BaseModel):
    target_program_id: str = Field(min_length=1)
    confirm: bool = False


class ProgramSwitchResponse(BaseModel):
    status: str
    current_program_id: str
    target_program_id: str
    recommended_program_id: str
    reason: str
    rationale: str
    decision_trace: dict[str, Any]
    requires_confirmation: bool
    applied: bool


class ProgramTemplateSummary(BaseModel):
    id: str
    name: str
    version: str
    split: str
    days_supported: list[int]
    session_count: int
    description: str


class GuideProgramSummary(BaseModel):
    id: str
    name: str
    split: str
    days_supported: list[int]
    description: str


class GuideDaySummary(BaseModel):
    day_index: int
    day_name: str
    exercise_count: int
    first_exercise_id: str | None = None


class GuideExerciseSummary(BaseModel):
    id: str
    primary_exercise_id: str | None = None
    name: str
    notes: str | None = None
    video_youtube_url: str | None = None


class ProgramGuideResponse(BaseModel):
    id: str
    name: str
    description: str
    split: str
    days_supported: list[int]
    days: list[GuideDaySummary]


class ProgramDayGuideResponse(BaseModel):
    program_id: str
    day_index: int
    day_name: str
    exercises: list[GuideExerciseSummary]


class ProgramExerciseGuideResponse(BaseModel):
    program_id: str
    exercise: GuideExerciseSummary


class WorkoutSetLogRequest(BaseModel):
    primary_exercise_id: str | None = None
    exercise_id: str
    set_index: int = Field(ge=1)
    reps: int = Field(ge=1)
    weight: float = Field(gt=0)
    rpe: float | None = None


class WorkoutSubstitutionRecommendationResponse(BaseModel):
    recommended_name: str
    compatible_substitutions: list[str]
    failed_exposure_count: int
    trigger_threshold: int
    reason: str
    decision_trace: dict[str, Any]


class WorkoutLiveRecommendationResponse(BaseModel):
    completed_sets: int
    remaining_sets: int
    recommended_reps_min: int
    recommended_reps_max: int
    recommended_weight: float
    guidance: str
    guidance_rationale: str
    decision_trace: dict[str, Any]
    substitution_recommendation: WorkoutSubstitutionRecommendationResponse | None = None


class WorkoutSetLogResponse(BaseModel):
    id: str
    primary_exercise_id: str
    exercise_id: str
    set_index: int
    reps: int
    weight: float
    planned_reps_min: int
    planned_reps_max: int
    planned_weight: float
    rep_delta: int
    weight_delta: float
    next_working_weight: float
    guidance: str
    guidance_rationale: str
    decision_trace: dict[str, Any]
    starting_load_decision_trace: dict[str, Any] | None = None
    live_recommendation: WorkoutLiveRecommendationResponse
    created_at: datetime


class WorkoutExerciseSummaryResponse(BaseModel):
    exercise_id: str
    primary_exercise_id: str | None = None
    name: str
    planned_sets: int
    planned_reps_min: int
    planned_reps_max: int
    planned_weight: float
    performed_sets: int
    average_performed_reps: float
    average_performed_weight: float
    completion_pct: int
    rep_delta: float
    weight_delta: float
    next_working_weight: float
    guidance: str
    guidance_rationale: str
    decision_trace: dict[str, Any]


class WorkoutSummaryResponse(BaseModel):
    workout_id: str
    completed_total: int
    planned_total: int
    percent_complete: int
    overall_guidance: str
    overall_rationale: str
    decision_trace: dict[str, Any]
    exercises: list[WorkoutExerciseSummaryResponse]
