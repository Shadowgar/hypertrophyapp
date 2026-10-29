from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import auth_limits
from app.routers import auth
from app.schemas import LoginRequest, RegisterRequest, PasswordResetRequest, PasswordResetConfirmRequest


@pytest.mark.parametrize("operation,handler,payload,identity", [
    ("login", auth.login, LoginRequest(email="target@example.com", password="Synthetic-password"), "target@example.com"),
    ("register", auth.register, RegisterRequest(email="target@example.com", password="Synthetic-password", name="Synthetic"), "target@example.com"),
    ("request", auth.password_reset_request, PasswordResetRequest(email="target@example.com"), "target@example.com"),
    ("confirm", auth.password_reset_confirm, PasswordResetConfirmRequest(token="synthetic-reset-credential", new_password="Synthetic-password"), "synthetic-reset-credential"),
])
def test_rejected_auth_request_never_reaches_database_hashing_or_mail(monkeypatch, operation, handler, payload, identity):
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected attempt reached expensive or private work")
    for name in ("hash_password", "verify_password", "hash_password_reset_token", "send_password_reset_email", "is_smtp_configured"):
        monkeypatch.setattr(auth, name, forbidden)
    limit, _ = auth_limits.auth_attempts.policies[operation]
    for _ in range(limit):
        auth_limits.auth_attempts.check(operation, identity)
    with pytest.raises(HTTPException) as rejected:
        handler(payload, SimpleNamespace(query=forbidden))
    assert rejected.value.status_code == 429
    assert int(rejected.value.headers["Retry-After"]) > 0


def test_random_targets_share_global_budget_and_recover_after_window():
    now = [0.0]
    limiter = auth_limits.AuthAttemptLimiter(clock=lambda: now[0])
    for i in range(60):
        limiter.check("confirm", f"synthetic-random-{i}")
    with pytest.raises(HTTPException):
        limiter.check("confirm", "another-random-target")
    now[0] = 61
    limiter.check("confirm", "another-random-target")
    assert all(isinstance(key[1], bytes) and len(key[1]) == 32 for key in limiter.targets)


def test_account_limits_are_atomic_across_threads_and_expire():
    now = [0.0]
    limiter = auth_limits.AuthAttemptLimiter(clock=lambda: now[0])
    def attempt(_):
        try:
            limiter.check("login", "same-normalized-account")
            return True
        except HTTPException:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(30))) == 10
    now[0] = 61
    assert attempt(None)


def test_identity_capacity_fails_closed_and_expires():
    now = [0.0]
    limiter = auth_limits.AuthAttemptLimiter(clock=lambda: now[0], max_targets=2)
    limiter.check("request", "one")
    limiter.check("request", "two")
    with pytest.raises(HTTPException):
        limiter.check("request", "three")
    assert len(limiter.targets) == 2
    now[0] = 901
    limiter.check("request", "three")
    assert len(limiter.targets) == 1


def test_target_rejections_do_not_exhaust_other_accounts_budget():
    limiter = auth_limits.AuthAttemptLimiter()
    for _ in range(10):
        limiter.check("login", "attacker-selected-account")
    for _ in range(100):
        with pytest.raises(HTTPException):
            limiter.check("login", "attacker-selected-account")
    limiter.check("login", "unrelated-account")
    assert len(limiter.global_attempts) == 11


def test_expensive_auth_concurrency_is_bounded_and_slots_are_released():
    active = [auth_limits.limit_auth_concurrency() for _ in range(4)]
    for admission in active:
        next(admission)
    try:
        with pytest.raises(HTTPException) as rejected:
            next(auth_limits.limit_auth_concurrency())
        assert rejected.value.status_code == 429
    finally:
        for admission in active:
            admission.close()
    later = auth_limits.limit_auth_concurrency()
    next(later)
    later.close()


def test_new_password_byte_bound_prevents_silent_bcrypt_truncation():
    for value in ("a" * 73, "é" * 37):
        with pytest.raises(ValueError):
            RegisterRequest(email="synthetic@example.com", name="Synthetic", password=value)
        with pytest.raises(ValueError):
            PasswordResetConfirmRequest(token="synthetic-reset-credential", new_password=value)
    assert RegisterRequest(email="synthetic@example.com", name="Synthetic", password="é" * 36)
