from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..emailer import is_smtp_configured, send_password_reset_email
from ..models import PasswordResetToken, User
from ..models import BodyMeasurementEntry, CoachingRecommendation, ExerciseState, SorenessEntry, WeeklyCheckin, WeeklyReviewCycle
from ..models import WorkoutLogCommand, WorkoutOccurrence, WorkoutPlan, WorkoutSessionState, WorkoutSetLog
from ..observability import log_event
from ..schemas import (
    DevWipeUserRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RegisterRequest,
    StatusResponse,
    TokenResponse,
)
from ..security import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    hash_password_reset_token,
    verify_password,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already used")

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/dev/wipe-user")
def dev_wipe_user(payload: DevWipeUserRequest, db: DbSession) -> StatusResponse:
    if not settings.allow_dev_wipe_endpoints:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev wipe endpoints disabled")
    if payload.confirmation.strip().upper() != "WIPE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation must be WIPE")

    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if user is None:
        return StatusResponse(status="already_absent")

    user_id = user.id
    db.query(WorkoutLogCommand).filter(WorkoutLogCommand.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutOccurrence).filter(WorkoutOccurrence.user_id == user_id).delete(synchronize_session=False)
    db.query(ExerciseState).filter(ExerciseState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyReviewCycle).filter(WeeklyReviewCycle.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyCheckin).filter(WeeklyCheckin.user_id == user_id).delete(synchronize_session=False)
    db.query(SorenessEntry).filter(SorenessEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(BodyMeasurementEntry).filter(BodyMeasurementEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(CoachingRecommendation).filter(CoachingRecommendation.user_id == user_id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()
    return StatusResponse(status="wiped")


@router.post("/password-reset/request")
def password_reset_request(payload: PasswordResetRequest, db: DbSession) -> PasswordResetRequestResponse:
    accepted = PasswordResetRequestResponse(status="accepted", reset_token=None)
    if not is_smtp_configured(settings):
        log_event("password_reset_delivery_unavailable", level="warning")
        return accepted

    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not user:
        return accepted

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    reset_token = create_password_reset_token()
    entry = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(reset_token),
        # Persist an already-expired credential first. Failed/uncertain delivery
        # cannot leave it usable or require a compensation write.
        expires_at=datetime.min,
    )
    db.add(entry)
    try:
        db.commit()
        delivery = send_password_reset_email(to_email=normalized_email, reset_token=reset_token, config=settings)
        if delivery.sent:
            # A newer request can supersede this row while SMTP is in flight.
            # Never reactivate a credential already marked used by that request.
            db.query(PasswordResetToken).filter(
                PasswordResetToken.id == entry.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at == datetime.min,
            ).update({PasswordResetToken.expires_at: now + timedelta(minutes=30)}, synchronize_session=False)
            db.commit()
        else:
            log_event("password_reset_delivery_failed", level="warning")
    except Exception:
        try:
            db.rollback()
        except Exception:
            log_event("password_reset_rollback_failed", level="error")
        log_event("password_reset_operation_failed", level="error")
    return accepted


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirmRequest, db: DbSession) -> StatusResponse:
    token_hash = hash_password_reset_token(payload.token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entry = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == entry.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token user")

    user.password_hash = hash_password(payload.new_password)
    entry.used_at = now
    db.add(user)
    db.add(entry)
    db.commit()
    return StatusResponse(status="password_updated")
