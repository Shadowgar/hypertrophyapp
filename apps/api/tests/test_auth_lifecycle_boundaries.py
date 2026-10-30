"""Credential revocation and one-winner recovery on verified disposable targets."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Barrier, Event, local
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import event
from starlette.requests import Request

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.deps import get_current_user
from app.models import PasswordResetToken, User
from app.routers import auth
from app.routers.auth import password_reset_confirm
from app.schemas import PasswordResetConfirmRequest
from app.schemas import PasswordResetRequest
from app.emailer import EmailDeliveryResult
from app.security import create_access_token, hash_password, hash_password_reset_token, verify_password


def _authenticate(claims, password_hash="synthetic-credential"):
    user = SimpleNamespace(id="synthetic-user", password_hash=password_hash)
    query = SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: user))
    db = SimpleNamespace(query=lambda *_: query)
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return get_current_user(Request({"type": "http", "headers": []}), HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)


def _claims():
    return {"sub": "synthetic-user", "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()), "cv": sha256(b"synthetic-credential").hexdigest()}


@pytest.mark.parametrize("field,value", [("sub", None), ("sub", 123), ("sub", ""), ("exp", None), ("exp", "9999999999"), ("exp", float("inf")), ("cv", None), ("cv", []), ("cv", "wrong")])
def test_missing_or_malformed_required_claim_fails_closed(field, value):
    claims = _claims()
    if value is None:
        claims.pop(field)
    else:
        claims[field] = value
    with pytest.raises(HTTPException) as rejected:
        _authenticate(claims)
    assert rejected.value.status_code == 401


def test_current_credential_accepted_and_changed_credential_rejected():
    assert _authenticate(_claims()).id == "synthetic-user"
    with pytest.raises(HTTPException) as rejected:
        _authenticate(_claims(), "changed-credential")
    assert rejected.value.status_code == 401


@pytest.fixture
def recovery_account():
    # conftest validates the explicit disposable target before importing app.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = User(email=f"recovery-{uuid4().hex}@example.com", name="Synthetic", password_hash=hash_password("Original-password-123"))
        db.add(user)
        db.commit()
        yield user.id, user.password_hash


def _insert_tokens(user_id, values):
    with SessionLocal() as db:
        for value in values:
            db.add(PasswordResetToken(user_id=user_id, token_hash=hash_password_reset_token(value), expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)))
        db.commit()


@pytest.mark.parametrize("same_token", [True, False])
def test_competing_resets_have_one_winner(recovery_account, same_token):
    user_id, _ = recovery_account
    tokens = [f"synthetic-reset-{uuid4().hex}", f"synthetic-reset-{uuid4().hex}"]
    _insert_tokens(user_id, tokens)
    barrier, seen = Barrier(2), local()

    def synchronize_initial_lookup(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "password_reset_tokens" in statement and not getattr(seen, "waited", False):
            seen.waited = True
            barrier.wait(timeout=10)

    def submit(index):
        with SessionLocal() as db:
            try:
                password_reset_confirm(PasswordResetConfirmRequest(token=tokens[0 if same_token else index], new_password=f"New-password-{index}-123"), db)
                return 200, index
            except HTTPException as exc:
                db.rollback()
                return exc.status_code, index

    event.listen(engine, "before_cursor_execute", synchronize_initial_lookup)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_initial_lookup)
    assert sorted(status for status, _ in results) == [200, 400]
    winner = next(index for status, index in results if status == 200)
    with SessionLocal() as db:
        assert verify_password(f"New-password-{winner}-123", db.get(User, user_id).password_hash)
        assert db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)).count() == 0


def test_failed_reset_commit_does_not_change_password_or_consume_tokens(recovery_account, monkeypatch):
    user_id, original_hash = recovery_account
    token = f"synthetic-rollback-reset-{uuid4().hex}"
    _insert_tokens(user_id, [token])
    with SessionLocal() as db:
        monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("injected transaction failure")))
        with pytest.raises(RuntimeError):
            password_reset_confirm(PasswordResetConfirmRequest(token=token, new_password="Changed-password-123"), db)
        db.rollback()
    with SessionLocal() as db:
        assert db.get(User, user_id).password_hash == original_hash
        assert db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)).count() == 1


def test_request_supersession_during_delivery_cannot_revive_old_token(recovery_account, monkeypatch):
    user_id, original_hash = recovery_account
    old_token = f"synthetic-old-{uuid4().hex}"
    _insert_tokens(user_id, [old_token])
    entered, release = Event(), Event()
    delivered = []
    monkeypatch.setattr(auth, "is_smtp_configured", lambda _: True)
    def mail(**kwargs):
        delivered.append(kwargs["reset_token"])
        entered.set()
        assert release.wait(10)
        return EmailDeliveryResult(sent=True)
    monkeypatch.setattr(auth, "send_password_reset_email", mail)
    with SessionLocal() as db:
        email = db.get(User, user_id).email
    def request():
        with SessionLocal() as db:
            return auth.password_reset_request(PasswordResetRequest(email=email), db)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(request)
        assert entered.wait(10)
        try:
            with SessionLocal() as db:
                with pytest.raises(HTTPException) as rejected:
                    password_reset_confirm(PasswordResetConfirmRequest(token=old_token, new_password="Rejected-password-123"), db)
                assert rejected.value.status_code == 400
        finally:
            release.set()
        assert future.result(timeout=10).status == "accepted"
    with SessionLocal() as db:
        assert db.get(User, user_id).password_hash == original_hash
        assert db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)).count() == 1
        assert password_reset_confirm(PasswordResetConfirmRequest(token=delivered[0], new_password="Accepted-password-123"), db).status == "password_updated"


def test_expiry_is_rechecked_after_waiting_for_account_lock(recovery_account):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires verified PostgreSQL row locks")
    user_id, original_hash = recovery_account
    token = f"synthetic-expiry-{uuid4().hex}"
    _insert_tokens(user_id, [token])
    reached = Event()
    def observe(conn, cursor, statement, parameters, context, executemany):
        if "FOR UPDATE" in statement:
            reached.set()
    def confirm():
        with SessionLocal() as db:
            try:
                password_reset_confirm(PasswordResetConfirmRequest(token=token, new_password="Rejected-password-123"), db)
                return 200
            except HTTPException as exc:
                return exc.status_code
    with SessionLocal() as holder:
        holder.query(User).filter(User.id == user_id).with_for_update().one()
        event.listen(engine, "before_cursor_execute", observe)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(confirm)
                assert reached.wait(10)
                holder.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).update({PasswordResetToken.expires_at: datetime.min})
                holder.commit()
                assert future.result(timeout=10) == 400
        finally:
            event.remove(engine, "before_cursor_execute", observe)
    with SessionLocal() as db:
        assert db.get(User, user_id).password_hash == original_hash
