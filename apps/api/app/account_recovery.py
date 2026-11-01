"""Account-locked recovery authority; no mail or prescription/data mutation."""
from datetime import datetime, timezone
from hashlib import sha256
import secrets
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .deps import assert_current_credential
from .models import AccountRecoveryCode, AccountSecurityEvent, PasswordResetToken, User
from .security import hash_password, hash_password_reset_token, verify_password


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_recovery_code(code: str) -> str:
    # Domain separation and 256 bits of independent random input. Not a
    # password hash and deliberately independent of JWT signing-key rotation.
    return sha256(b'ferravis/account-recovery/v1\x00'+code.encode()).hexdigest()


def active_codes(db, user_id):
    return db.query(AccountRecoveryCode).filter(AccountRecoveryCode.user_id == user_id,
        AccountRecoveryCode.used_at.is_(None), AccountRecoveryCode.revoked_at.is_(None))


def generate_codes(db: Session, user_id: str, credential_version: str, current_password: str, command_id: str) -> dict:
    user = db.query(User).filter_by(id=user_id).populate_existing().with_for_update().first()
    if user is None:
        raise HTTPException(401, 'Invalid credentials')
    assert_current_credential(user, credential_version)
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(401, 'Invalid credentials')
    if db.query(AccountSecurityEvent.id).filter_by(user_id=user_id, command_id=command_id).first():
        return {'status': 'already_processed', 'codes': []}
    now, batch = now_utc(), str(uuid4())
    revoked = active_codes(db, user_id).update({AccountRecoveryCode.revoked_at: now}, synchronize_session=False)
    codes = ['frc_'+secrets.token_urlsafe(32) for _ in range(10)]
    db.add_all(AccountRecoveryCode(user_id=user_id, batch_id=batch, code_hash=hash_recovery_code(code)) for code in codes)
    if revoked:
        db.add(AccountSecurityEvent(user_id=user_id, kind='recovery_codes_revoked', batch_id=batch))
    db.add(AccountSecurityEvent(user_id=user_id, kind='recovery_codes_generated', command_id=command_id, batch_id=batch))
    db.commit()
    return {'status': 'generated', 'codes': codes}


def invalid():
    return HTTPException(400, 'Invalid or expired reset token')


def confirm_recovery(db: Session, token: str, new_password: str) -> None:
    # Resolve authority from stored rows, never from a prefix that an existing
    # random short-lived token may coincidentally share.
    model = AccountRecoveryCode
    match = model.code_hash == hash_recovery_code(token)
    owner = db.query(model.user_id).filter(match).first()
    permanent = owner is not None
    if not permanent:
        model = PasswordResetToken
        match = model.token_hash == hash_password_reset_token(token)
        owner = db.query(model.user_id).filter(match).first()
    if owner is None:
        raise invalid()
    user = db.query(User).filter_by(id=owner.user_id).populate_existing().with_for_update().first()
    if user is None:
        raise invalid()
    now = now_utc()
    query = db.query(model).filter(match, model.user_id == user.id, model.used_at.is_(None))
    if permanent:
        query = query.filter(model.revoked_at.is_(None))
    else:
        query = query.filter(model.expires_at > now)
    # CAS protects single use even where FOR UPDATE isn't available (SQLite).
    if query.update({model.used_at: now}, synchronize_session=False) != 1:
        db.rollback()
        raise invalid()
    user.password_hash = hash_password(new_password)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    if not permanent:
        revoked = active_codes(db, user.id).update({AccountRecoveryCode.revoked_at: now}, synchronize_session=False)
        if revoked:
            db.add(AccountSecurityEvent(user_id=user.id, kind='recovery_codes_revoked'))
    db.add(AccountSecurityEvent(user_id=user.id, kind='password_recovered'))
    db.commit()


def recovery_status(db: Session, user_id: str) -> dict:
    events = db.query(AccountSecurityEvent).filter_by(user_id=user_id).order_by(AccountSecurityEvent.created_at.desc(), AccountSecurityEvent.id.desc()).limit(50).all()
    return {'remaining': active_codes(db, user_id).count(), 'events': [
        {'id': e.id, 'kind': e.kind, 'created_at': e.created_at,
         'acknowledged_at': e.acknowledged_at} for e in events]}
