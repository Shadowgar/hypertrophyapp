"""Authenticated Flexible training commands; deterministic decision owner is flexible_training."""
from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from .. import flexible_training as lifecycle

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class EnrollmentPreview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    program_id: str
    timezone: str = Field(min_length=1, max_length=64)
    expected_sessions_per_week: int | None = Field(default=None, ge=1, le=7, strict=True)
    switch_plan_id: str | None = None


class Enrollment(EnrollmentPreview):
    preview_digest: str = Field(min_length=64, max_length=64)
    command_id: str = Field(min_length=1, max_length=128)
    confirmed: bool = Field(strict=True)


class SequenceCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=1, strict=True)
    occurrence_id: str | None
    expected_digest: str = Field(min_length=64, max_length=64)
    expected_local_day: date
    confirmed: bool = Field(strict=True)
    reason: str | None = Field(default=None, max_length=500)


@router.get('/training/next')
def next_workout(db: Db, current_user: CurrentUser):
    return lifecycle.next_training(db, current_user)


@router.post('/training/enroll/preview')
def preview(payload: EnrollmentPreview, db: Db, current_user: CurrentUser):
    return lifecycle.enrollment_preview(db, current_user, payload)[0]


@router.post('/training/enroll')
def enroll(payload: Enrollment, db: Db, current_user: CurrentUser):
    return lifecycle.enroll(db, current_user, payload)


@router.post('/training/{sequence_id}/{operation}')
def command(sequence_id: str, operation: str, payload: SequenceCommand, db: Db, current_user: CurrentUser):
    return lifecycle.command(db, current_user, sequence_id, operation, payload)
