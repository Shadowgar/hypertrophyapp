from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String
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
