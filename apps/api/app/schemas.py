from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


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


class ProfileUpsert(BaseModel):
    name: str
    age: int
    weight: float
    gender: str
    split_preference: str
    days_available: int = Field(ge=2, le=4)
    nutrition_phase: str
    calories: int
    protein: int
    fat: int
    carbs: int


class ProfileResponse(ProfileUpsert):
    email: EmailStr


class WeeklyCheckinRequest(BaseModel):
    week_start: date
    body_weight: float
    adherence_score: int = Field(ge=1, le=5)
    notes: str | None = None


class GenerateWeekPlanRequest(BaseModel):
    template_id: str = "full_body_v1"


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
