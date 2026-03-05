from datetime import date, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_history_weekly_checkins")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "history-weekly@example.com", credential_field: "HistoryPass1", "name": "History User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def test_weekly_checkin_history_returns_sorted_entries_and_limit() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    current_monday = _current_monday()
    previous_monday = current_monday - timedelta(days=7)

    first = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": previous_monday.isoformat(),
            "body_weight": 82.2,
            "adherence_score": 3,
            "notes": "Previous week",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": current_monday.isoformat(),
            "body_weight": 81.7,
            "adherence_score": 5,
            "notes": "Current week",
        },
    )
    assert second.status_code == 200

    history = client.get("/history/weekly-checkins", headers=headers)
    assert history.status_code == 200
    payload = history.json()

    assert len(payload["entries"]) == 2
    assert payload["entries"][0]["week_start"] == previous_monday.isoformat()
    assert payload["entries"][1]["week_start"] == current_monday.isoformat()
    assert payload["entries"][1]["adherence_score"] == 5

    limited = client.get("/history/weekly-checkins?limit=1", headers=headers)
    assert limited.status_code == 200
    limited_payload = limited.json()
    assert len(limited_payload["entries"]) == 1
    assert limited_payload["entries"][0]["week_start"] == current_monday.isoformat()
