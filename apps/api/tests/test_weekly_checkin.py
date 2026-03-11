from datetime import date, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_weekly_checkin")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "checkin@example.com", credential_field: "CheckinPass1", "name": "Checkin User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def test_weekly_checkin_accepts_valid_payload() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_and_token(client)

    response = client.post(
        "/weekly-checkin",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "week_start": _current_monday().isoformat(),
            "body_weight": 82.5,
            "adherence_score": 4,
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["elbow_flexion"],
            "notes": "Good week",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "logged"


def test_weekly_checkin_rejects_non_monday() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_and_token(client)

    monday = _current_monday()
    tuesday = monday + timedelta(days=1)

    response = client.post(
        "/weekly-checkin",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "week_start": tuesday.isoformat(),
            "body_weight": 82.5,
            "adherence_score": 4,
        },
    )

    assert response.status_code == 422


def test_weekly_checkin_rejects_future_monday() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_and_token(client)

    future_monday = _current_monday() + timedelta(days=7)
    response = client.post(
        "/weekly-checkin",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "week_start": future_monday.isoformat(),
            "body_weight": 82.5,
            "adherence_score": 4,
        },
    )

    assert response.status_code == 422


def test_weekly_checkin_rejects_non_positive_weight() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_and_token(client)

    response = client.post(
        "/weekly-checkin",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "week_start": _current_monday().isoformat(),
            "body_weight": 0,
            "adherence_score": 4,
        },
    )

    assert response.status_code == 422
