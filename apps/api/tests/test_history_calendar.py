from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_history_calendar")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutPlan, WorkoutSetLog


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "calendar@example.com", credential_field: "CalendarPass1", "name": "Calendar User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_history_calendar_and_day_detail() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    day_one = today - timedelta(days=2)
    day_two = today - timedelta(days=1)
    day_three = today

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "calendar@example.com").first()
        assert user is not None

        session.add_all(
            [
                WorkoutPlan(
                    user_id=user.id,
                    week_start=day_one - timedelta(days=day_one.weekday()),
                    split="full_body",
                    phase="accumulation",
                    payload={
                        "sessions": [
                            {
                                "session_id": "workout_a",
                                "date": day_one.isoformat(),
                                "exercises": [
                                    {"id": "bench_press", "name": "Bench Press", "sets": 3, "primary_muscles": ["chest"]},
                                ],
                            },
                            {
                                "session_id": "workout_c",
                                "date": day_three.isoformat(),
                                "exercises": [
                                    {"id": "incline_press", "name": "Incline Press", "sets": 2, "primary_muscles": ["chest"]},
                                ],
                            },
                        ],
                        "program_template_id": "pure_bodybuilding_phase_1_full_body",
                    },
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_a",
                    primary_exercise_id="bench_press",
                    exercise_id="bench_press",
                    set_index=1,
                    reps=8,
                    weight=80,
                    created_at=datetime.combine(day_one, time(9, 0)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_a",
                    primary_exercise_id="bench_press",
                    exercise_id="bench_press",
                    set_index=2,
                    reps=7,
                    weight=82.5,
                    created_at=datetime.combine(day_one, time(9, 5)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_b",
                    primary_exercise_id="romanian_deadlift",
                    exercise_id="romanian_deadlift",
                    set_index=1,
                    reps=10,
                    weight=100,
                    created_at=datetime.combine(day_two, time(10, 0)),
                ),
            ]
        )
        session.commit()

    start = (today - timedelta(days=3)).isoformat()
    end = today.isoformat()
    calendar = client.get(f"/history/calendar?start_date={start}&end_date={end}", headers=headers)
    assert calendar.status_code == 200
    calendar_payload = calendar.json()

    assert calendar_payload["start_date"] == start
    assert calendar_payload["end_date"] == end
    assert len(calendar_payload["days"]) == 4
    assert calendar_payload["active_days"] == 2
    assert calendar_payload["longest_streak_days"] >= 1

    day_one_entry = next(day for day in calendar_payload["days"] if day["date"] == day_one.isoformat())
    assert day_one_entry["set_count"] == 2
    assert day_one_entry["exercise_count"] == 1
    assert day_one_entry["completed"] is True
    assert day_one_entry["program_ids"] == ["pure_bodybuilding_phase_1_full_body"]
    assert day_one_entry["muscles"] == ["chest"]
    assert day_one_entry["pr_count"] == 1
    assert day_one_entry["pr_exercises"] == ["bench_press"]

    detail = client.get(f"/history/day/{day_one.isoformat()}", headers=headers)
    assert detail.status_code == 200
    detail_payload = detail.json()

    assert detail_payload["date"] == day_one.isoformat()
    assert detail_payload["totals"]["set_count"] == 2
    assert detail_payload["totals"]["planned_set_count"] == 3
    assert detail_payload["totals"]["set_delta"] == -1
    assert detail_payload["totals"]["exercise_count"] == 1
    assert len(detail_payload["workouts"]) == 1
    assert detail_payload["workouts"][0]["workout_id"] == "workout_a"
    assert detail_payload["workouts"][0]["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert detail_payload["workouts"][0]["planned_sets_total"] == 3
    assert detail_payload["workouts"][0]["set_delta"] == -1
    assert detail_payload["workouts"][0]["exercises"][0]["exercise_id"] == "bench_press"
    assert detail_payload["workouts"][0]["exercises"][0]["planned_name"] == "Bench Press"
    assert detail_payload["workouts"][0]["exercises"][0]["primary_muscles"] == ["chest"]
    assert detail_payload["workouts"][0]["exercises"][0]["planned_sets"] == 3
    assert detail_payload["workouts"][0]["exercises"][0]["set_delta"] == -1

    missed_detail = client.get(f"/history/day/{day_three.isoformat()}", headers=headers)
    assert missed_detail.status_code == 200
    missed_payload = missed_detail.json()
    assert missed_payload["totals"]["set_count"] == 0
    assert missed_payload["totals"]["planned_set_count"] == 2
    assert missed_payload["totals"]["set_delta"] == -2
    assert len(missed_payload["workouts"]) == 1
    assert missed_payload["workouts"][0]["workout_id"] == "workout_c"
    assert missed_payload["workouts"][0]["exercises"][0]["planned_name"] == "Incline Press"


def test_history_calendar_rejects_invalid_date_window() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/history/calendar?start_date=2026-03-10&end_date=2026-03-01",
        headers=headers,
    )
    assert response.status_code == 400
