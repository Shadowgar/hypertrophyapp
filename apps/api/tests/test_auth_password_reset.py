import os
from pathlib import Path

from fastapi.testclient import TestClient

DB_FILE = Path(__file__).resolve().parent / "test_auth_password_reset.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_password_reset_happy_path() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "reset@example.com", "password": "OldStrongPass1", "name": "Reset User"},
    )
    assert register.status_code == 200

    reset_request = client.post("/auth/password-reset/request", json={"email": "reset@example.com"})
    assert reset_request.status_code == 200
    payload = reset_request.json()
    assert payload["status"] == "accepted"
    assert payload["reset_token"]

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={"token": payload["reset_token"], "new_password": "NewStrongPass1"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "password_updated"

    old_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "OldStrongPass1"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "NewStrongPass1"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_password_reset_rejects_invalid_token() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "invalid@example.com", "password": "StartPass123", "name": "Invalid Token"},
    )
    assert register.status_code == 200

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={"token": "invalid-token-value", "new_password": "AnotherPass123"},
    )
    assert confirm.status_code == 400
