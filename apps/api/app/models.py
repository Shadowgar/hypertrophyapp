from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

USER_FK = "users.id"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    split_preference: Mapped[str | None] = mapped_column(String, nullable=True)
    selected_program_id: Mapped[str | None] = mapped_column(String, nullable=True)
    training_location: Mapped[str | None] = mapped_column(String, nullable=True)
    equipment_profile: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    days_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nutrition_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carbs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeeklyCheckin(Base):
    __tablename__ = "weekly_checkins"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    body_weight: Mapped[float] = mapped_column(Float)
    adherence_score: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeeklyReviewCycle(Base):
    __tablename__ = "weekly_review_cycles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    reviewed_on: Mapped[date] = mapped_column(Date, index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    previous_week_start: Mapped[date] = mapped_column(Date, index=True)
    body_weight: Mapped[float] = mapped_column(Float)
    calories: Mapped[int] = mapped_column(Integer)
    protein: Mapped[int] = mapped_column(Integer)
    fat: Mapped[int] = mapped_column(Integer)
    carbs: Mapped[int] = mapped_column(Integer)
    adherence_score: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    faults: Mapped[dict] = mapped_column(JSON)
    adjustments: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SorenessEntry(Base):
    __tablename__ = "soreness_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    severity_by_muscle: Mapped[dict[str, str]] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BodyMeasurementEntry(Base):
    __tablename__ = "body_measurement_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    measured_on: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    split: Mapped[str] = mapped_column(String)
    phase: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkoutSetLog(Base):
    __tablename__ = "workout_set_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    workout_id: Mapped[str] = mapped_column(String, index=True)
    primary_exercise_id: Mapped[str] = mapped_column(String, index=True)
    exercise_id: Mapped[str] = mapped_column(String, index=True)
    set_index: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExerciseState(Base):
    __tablename__ = "exercise_states"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    exercise_id: Mapped[str] = mapped_column(String, index=True)
    current_working_weight: Mapped[float] = mapped_column(Float, default=20)
    exposure_count: Mapped[int] = mapped_column(Integer, default=0)
    fatigue_score: Mapped[float] = mapped_column(Float, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkoutSessionState(Base):
    __tablename__ = "workout_session_states"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "workout_id",
            "exercise_id",
            name="uq_workout_session_states_user_workout_exercise",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey(USER_FK), index=True)
    workout_id: Mapped[str] = mapped_column(String, index=True)
    primary_exercise_id: Mapped[str] = mapped_column(String, index=True)
    exercise_id: Mapped[str] = mapped_column(String, index=True)

    planned_sets: Mapped[int] = mapped_column(Integer)
    planned_reps_min: Mapped[int] = mapped_column(Integer)
    planned_reps_max: Mapped[int] = mapped_column(Integer)
    planned_weight: Mapped[float] = mapped_column(Float)

    completed_sets: Mapped[int] = mapped_column(Integer, default=0)
    total_logged_reps: Mapped[int] = mapped_column(Integer, default=0)
    total_logged_weight: Mapped[float] = mapped_column(Float, default=0)
    set_history: Mapped[list[dict]] = mapped_column(JSON, default=list)

    remaining_sets: Mapped[int] = mapped_column(Integer, default=0)
    recommended_reps_min: Mapped[int] = mapped_column(Integer)
    recommended_reps_max: Mapped[int] = mapped_column(Integer)
    recommended_weight: Mapped[float] = mapped_column(Float)
    last_guidance: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
