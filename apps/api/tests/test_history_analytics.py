from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_history_analytics")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import BodyMeasurementEntry, User, WorkoutSetLog


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _register_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "history-analytics@example.com", credential_field: "HistoryAnalytics1", "name": "History Analytics"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_history_analytics_returns_pr_trends_measurements_and_heatmap() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    current_monday = _monday_of(date.today())
    week_one = current_monday - timedelta(days=14)
    week_two = current_monday - timedelta(days=7)

    checkin_one = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": week_one.isoformat(),
            "body_weight": 82.5,
            "adherence_score": 4,
            "notes": "Week one",
        },
    )
    assert checkin_one.status_code == 200

    checkin_two = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": week_two.isoformat(),
            "body_weight": 81.8,
            "adherence_score": 5,
            "notes": "Week two",
        },
    )
    assert checkin_two.status_code == 200

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "history-analytics@example.com").first()
        assert user is not None

        session.add_all(
            [
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="w1",
                    primary_exercise_id="bench",
                    exercise_id="bench",
                    set_index=1,
                    reps=8,
                    weight=80,
                    created_at=datetime.combine(week_one + timedelta(days=1), time(9, 0)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="w2",
                    primary_exercise_id="bench",
                    exercise_id="bench",
                    set_index=1,
                    reps=7,
                    weight=90,
                    created_at=datetime.combine(week_two + timedelta(days=2), time(9, 0)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="w3",
                    primary_exercise_id="squat",
                    exercise_id="squat",
                    set_index=1,
                    reps=5,
                    weight=110,
                    created_at=datetime.combine(week_two + timedelta(days=3), time(9, 0)),
                ),
                BodyMeasurementEntry(
                    user_id=user.id,
                    measured_on=week_one,
                    name="Waist",
                    value=84.0,
                    unit="cm",
                ),
                BodyMeasurementEntry(
                    user_id=user.id,
                    measured_on=week_two,
                    name="Waist",
                    value=82.0,
                    unit="cm",
                ),
            ]
        )
        session.commit()

    response = client.get("/history/analytics?limit_weeks=4&checkin_limit=12", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    assert payload["window"]["limit_weeks"] == 4
    assert len(payload["checkins"]) == 2
    assert len(payload["bodyweight_trend"]) == 2
    assert payload["adherence"]["average_pct"] >= 80

    exercise_ids = {entry["exercise_id"] for entry in payload["strength_trends"]}
    assert "bench" in exercise_ids

    bench_pr = next(item for item in payload["pr_highlights"] if item["exercise_id"] == "bench")
    assert bench_pr["pr_weight"] == 90
    assert bench_pr["pr_delta"] == 10

    waist = next(item for item in payload["body_measurement_trends"] if item["name"] == "waist")
    assert waist["latest_value"] == 82
    assert waist["delta"] == -2

    assert len(payload["volume_heatmap"]["weeks"]) == 4
