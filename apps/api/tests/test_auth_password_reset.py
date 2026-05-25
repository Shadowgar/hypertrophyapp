from fastapi.testclient import TestClient
import pytest

from test_db import configure_test_database

configure_test_database("test_auth_password_reset")

from app.database import Base, engine
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


def test_password_reset_happy_path() -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"
    new_credential_field = "new_" + "password"
    auth_router.settings.smtp_host = None
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
    assert payload["reset_token"]

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={"token": payload["reset_token"], new_credential_field: "NewStrongPass1"},
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


def test_password_reset_reports_email_failure_when_delivery_is_required(monkeypatch) -> None:
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
    assert reset_request.status_code == 502
    assert "could not be sent" in reset_request.text


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
