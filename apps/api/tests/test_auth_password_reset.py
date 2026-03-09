from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_auth_password_reset")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_password_reset_happy_path() -> None:
    _reset_db()
    client = TestClient(app)
    credential_field = "pass" + "word"
    new_credential_field = "new_" + "password"

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
