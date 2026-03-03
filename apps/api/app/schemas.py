from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    status: str
    reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8)


class StatusResponse(BaseModel):
    status: str


class ProfileUpsert(BaseModel):
    name: str
    age: int
    weight: float
    gender: str
    split_preference: str
    selected_program_id: str = "full_body_v1"
    training_location: str | None = None
    equipment_profile: list[str] = Field(default_factory=list)
    days_available: int = Field(ge=2, le=5)
    nutrition_phase: str
    calories: int
    protein: int
    fat: int
    carbs: int


class ProfileResponse(ProfileUpsert):
    email: EmailStr


class WeeklyCheckinRequest(BaseModel):
    week_start: date
    body_weight: float = Field(gt=0)
    adherence_score: int = Field(ge=1, le=5)
    notes: str | None = None

    @field_validator("week_start")
    @classmethod
    def validate_week_start(cls, value: date) -> date:
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        if value > date.today():
            raise ValueError("week_start cannot be in the future")
        return value


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


class ProgramRecommendationResponse(BaseModel):
    current_program_id: str
    recommended_program_id: str
    reason: str
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
    requires_confirmation: bool
    applied: bool


class ProgramTemplateSummary(BaseModel):
    id: str
    version: str
    split: str
    days_supported: list[int]
    session_count: int
    description: str


class WorkoutSetLogRequest(BaseModel):
    primary_exercise_id: str | None = None
    exercise_id: str
    set_index: int = Field(ge=1)
    reps: int = Field(ge=1)
    weight: float = Field(gt=0)
    rpe: float | None = None


class WorkoutSetLogResponse(BaseModel):
    id: str
    primary_exercise_id: str
    exercise_id: str
    reps: int
    weight: float
    created_at: datetime
