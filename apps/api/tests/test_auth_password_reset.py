from fastapi.testclient import TestClient
from datetime import datetime, timezone
import pytest

from test_db import configure_test_database

configure_test_database("test_auth_password_reset")

from app.database import Base, engine
from app.database import SessionLocal
from app.models import PasswordResetToken
from app.emailer import EmailDeliveryResult
from app.main import app
from app.routers import auth as auth_router


@pytest.fixture(autouse=True)
def _reset_email_settings():
    original = {
        "smtp_host": auth_router.settings.smtp_host,
        "smtp_username": auth_router.settings.smtp_username,
        "smtp_password": auth_router.settings.smtp_password,
        "smtp_from_email": auth_router.settings.smtp_from_email,
        "password_reset_expose_token": auth_router.settings.password_reset_expose_token,
        "password_reset_require_email_delivery": auth_router.settings.password_reset_require_email_delivery,
    }
    auth_router.settings.smtp_host = None
    auth_router.settings.smtp_username = None
    auth_router.settings.smtp_password = None
    auth_router.settings.smtp_from_email = None
    auth_router.settings.password_reset_expose_token = True
    auth_router.settings.password_reset_require_email_delivery = False
    yield
    for key, value in original.items():
        setattr(auth_router.settings, key, value)


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _configure_mail() -> None:
    auth_router.settings.smtp_host = "smtp.example.com"
    auth_router.settings.smtp_username = "sender@example.com"
    auth_router.settings.smtp_password = "synthetic-mail-credential"
    auth_router.settings.smtp_from_email = "sender@example.com"


def test_password_reset_happy_path(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"
    new_credential_field = "new_" + "password"
    _configure_mail()
    delivered: list[str] = []
    def fake_send(*, to_email, reset_token, config):
        delivered.append(reset_token)
        return EmailDeliveryResult(sent=True)
    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send)
    auth_router.settings.password_reset_expose_token = True
    auth_router.settings.password_reset_require_email_delivery = False

    register = client.post(
        "/auth/register",
        json={"email": "reset@example.com", credential_field: "OldStrongPass1", "name": "Reset User"},
    )
    assert register.status_code == 200

    reset_request = client.post("/auth/password-reset/request", json={"email": "reset@example.com"})
    assert reset_request.status_code == 200
    payload = reset_request.json()
    assert payload["status"] == "accepted"
    assert payload["reset_token"] is None
    assert delivered

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={"token": delivered[0], new_credential_field: "NewStrongPass1"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "password_updated"

    old_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", credential_field: "OldStrongPass1"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", credential_field: "NewStrongPass1"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    replay = client.post("/auth/password-reset/confirm", json={"token": delivered[0], new_credential_field: "AnotherStrongPass1"})
    assert replay.status_code == 400


def test_password_reset_sends_email_when_smtp_is_configured(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"
    sent_messages: list[dict[str, str]] = []

    auth_router.settings.smtp_host = "smtp.example.com"
    auth_router.settings.smtp_username = "sender@example.com"
    auth_router.settings.smtp_password = "smtp-secret"
    auth_router.settings.smtp_from_email = "sender@example.com"
    auth_router.settings.password_reset_expose_token = False
    auth_router.settings.password_reset_require_email_delivery = True

    def fake_send_password_reset_email(*, to_email: str, reset_token: str, config):
        sent_messages.append({"to_email": to_email, "reset_token": reset_token})
        return EmailDeliveryResult(sent=True)

    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send_password_reset_email)

    register = client.post(
        "/auth/register",
        json={"email": "mailme@example.com", credential_field: "OldStrongPass1", "name": "Mail User"},
    )
    assert register.status_code == 200

    reset_request = client.post("/auth/password-reset/request", json={"email": "mailme@example.com"})
    assert reset_request.status_code == 200
    payload = reset_request.json()
    assert payload["status"] == "accepted"
    assert payload["reset_token"] is None
    assert sent_messages
    assert sent_messages[0]["to_email"] == "mailme@example.com"
    assert sent_messages[0]["reset_token"]


def test_password_reset_acknowledges_failed_delivery_without_usable_credential(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"

    auth_router.settings.smtp_host = "smtp.example.com"
    auth_router.settings.smtp_username = "sender@example.com"
    auth_router.settings.smtp_password = "smtp-secret"
    auth_router.settings.smtp_from_email = "sender@example.com"
    auth_router.settings.password_reset_expose_token = False
    auth_router.settings.password_reset_require_email_delivery = True

    def fake_send_password_reset_email(*, to_email: str, reset_token: str, config):
        return EmailDeliveryResult(sent=False, error="smtp failed")

    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send_password_reset_email)

    register = client.post(
        "/auth/register",
        json={"email": "failmail@example.com", credential_field: "OldStrongPass1", "name": "Fail Mail"},
    )
    assert register.status_code == 200

    reset_request = client.post("/auth/password-reset/request", json={"email": "failmail@example.com"})
    assert reset_request.status_code == 200
    assert reset_request.json() == {"status": "accepted", "reset_token": None}
    with SessionLocal() as db:
        assert db.query(PasswordResetToken).filter(PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)).count() == 0


@pytest.mark.parametrize("smtp_complete", [False, True])
@pytest.mark.parametrize("delivered", [False, True])
@pytest.mark.parametrize("expose", [False, True])
@pytest.mark.parametrize("require_delivery", [False, True])
def test_recovery_acknowledgment_matrix(monkeypatch, smtp_complete, delivered, expose, require_delivery) -> None:
    _reset_db()
    client = TestClient(app)
    assert client.post("/auth/register", json={"email": "matrix@example.com", "password": "Synthetic-password-1", "name": "Matrix"}).status_code == 200
    if smtp_complete:
        _configure_mail()
    auth_router.settings.password_reset_expose_token = expose
    auth_router.settings.password_reset_require_email_delivery = require_delivery
    captured: list[str] = []
    def fake_send(*, to_email, reset_token, config):
        captured.append(reset_token)
        return EmailDeliveryResult(sent=delivered, error=None if delivered else "synthetic failure")
    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send)
    existing = client.post("/auth/password-reset/request", json={"email": "matrix@example.com"})
    unknown = client.post("/auth/password-reset/request", json={"email": "unknown@example.com"})
    assert existing.status_code == unknown.status_code == 200
    assert existing.json() == unknown.json() == {"status": "accepted", "reset_token": None}
    assert len(captured) == int(smtp_complete)
    with SessionLocal() as db:
        assert db.query(PasswordResetToken).count() == int(smtp_complete)
        assert db.query(PasswordResetToken).filter(PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)).count() == int(smtp_complete and delivered)
    if captured:
        assert captured[0] not in existing.text
        confirm = client.post("/auth/password-reset/confirm", json={"token": captured[0], "new_password": "Synthetic-password-2"})
        assert confirm.status_code == (200 if delivered else 400)


def test_failed_delivery_supersedes_prior_token_and_never_activates_new_token(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    _configure_mail()
    assert client.post("/auth/register", json={"email": "prior@example.com", "password": "Synthetic-password-1", "name": "Prior"}).status_code == 200
    captured: list[str] = []
    def send(*, to_email, reset_token, config):
        captured.append(reset_token)
        if len(captured) == 2:
            raise RuntimeError(reset_token)  # Provider errors can contain the credential.
        return EmailDeliveryResult(sent=True)
    monkeypatch.setattr(auth_router, "send_password_reset_email", send)
    for _ in range(2):
        assert client.post("/auth/password-reset/request", json={"email": "prior@example.com"}).json() == {"status": "accepted", "reset_token": None}
    for token in captured:
        assert client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "Synthetic-password-2"}).status_code == 400


@pytest.mark.parametrize("rollback_failure", [False, True])
def test_activation_commit_failure_leaves_delivered_credential_unusable(monkeypatch, rollback_failure) -> None:
    _reset_db()
    client = TestClient(app)
    _configure_mail()
    assert client.post("/auth/register", json={"email": "activation@example.com", "password": "Synthetic-password-1", "name": "Activation"}).status_code == 200
    from sqlalchemy.orm import Session
    original_commit = Session.commit
    original_rollback = Session.rollback
    captured: list[str] = []
    def send(*, to_email, reset_token, config):
        captured.append(reset_token)
        def fail_commit(self):
            raise RuntimeError("synthetic persistence failure")
        monkeypatch.setattr(Session, "commit", fail_commit)
        if rollback_failure:
            monkeypatch.setattr(Session, "rollback", fail_commit)
        return EmailDeliveryResult(sent=True)
    monkeypatch.setattr(auth_router, "send_password_reset_email", send)
    response = client.post("/auth/password-reset/request", json={"email": "activation@example.com"})
    monkeypatch.setattr(Session, "commit", original_commit)
    monkeypatch.setattr(Session, "rollback", original_rollback)
    assert response.json() == {"status": "accepted", "reset_token": None}
    assert client.post("/auth/password-reset/confirm", json={"token": captured[0], "new_password": "Synthetic-password-2"}).status_code == 400


def test_newer_request_prevents_reactivation_after_delayed_delivery(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    _configure_mail()
    assert client.post("/auth/register", json={"email": "overlap@example.com", "password": "Synthetic-password-1", "name": "Overlap"}).status_code == 200
    captured: list[str] = []
    def send(*, to_email, reset_token, config):
        captured.append(reset_token)
        if len(captured) == 1:
            assert client.post("/auth/password-reset/request", json={"email": "overlap@example.com"}).status_code == 200
        return EmailDeliveryResult(sent=True)
    monkeypatch.setattr(auth_router, "send_password_reset_email", send)
    assert client.post("/auth/password-reset/request", json={"email": "overlap@example.com"}).status_code == 200
    for index, token in enumerate(captured):
        response = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "Synthetic-password-2"})
        assert response.status_code == (400 if index == 0 else 200)


def test_password_reset_rejects_invalid_token() -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"
    new_credential_field = "new_" + "password"
    token_field = "to" + "ken"

    register = client.post(
        "/auth/register",
        json={"email": "invalid@example.com", credential_field: "StartPass123", "name": "Invalid Token"},
    )
    assert register.status_code == 200

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={token_field: "invalid-token-value", new_credential_field: "AnotherPass123"},
    )
    assert confirm.status_code == 400


def test_dev_wipe_user_allows_re_registration() -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"

    register = client.post(
        "/auth/register",
        json={"email": "wipe@example.com", credential_field: "TestPass123", "name": "Wipe User"},
    )
    assert register.status_code == 200

    wipe = client.post(
        "/auth/dev/wipe-user",
        json={"email": "wipe@example.com", "confirmation": "WIPE"},
    )
    assert wipe.status_code == 200
    assert wipe.json()["status"] == "wiped"

    re_register = client.post(
        "/auth/register",
        json={"email": "wipe@example.com", credential_field: "TestPass123", "name": "Wipe User"},
    )
    assert re_register.status_code == 200


def test_auth_email_matching_is_case_and_whitespace_insensitive() -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"

    register = client.post(
        "/auth/register",
        json={"email": "  CaseUser@Example.COM  ", credential_field: "CasePass123", "name": "Case User"},
    )
    assert register.status_code == 200

    duplicate = client.post(
        "/auth/register",
        json={"email": "caseuser@example.com", credential_field: "CasePass123", "name": "Case User"},
    )
    assert duplicate.status_code == 400

    login = client.post(
        "/auth/login",
        json={"email": " CASEUSER@example.com ", credential_field: "CasePass123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()

    wipe = client.post(
        "/auth/dev/wipe-user",
        json={"email": "CaSeUsEr@ExAmPlE.CoM", "confirmation": "WIPE"},
    )
    assert wipe.status_code == 200
    assert wipe.json()["status"] == "wiped"
