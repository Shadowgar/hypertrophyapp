from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PasswordResetToken, User
from ..schemas import (
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
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already used")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/password-reset/request")
def password_reset_request(payload: PasswordResetRequest, db: DbSession) -> PasswordResetRequestResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return PasswordResetRequestResponse(status="accepted")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    reset_token = create_password_reset_token()
    entry = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(reset_token),
        expires_at=now + timedelta(minutes=30),
    )
    db.add(entry)
    db.commit()

    return PasswordResetRequestResponse(status="accepted", reset_token=reset_token)


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
