import os
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

DB_FILE = Path(__file__).resolve().parent / "test_workout_resume.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    response = client.post(
        "/auth/register",
        json={"email": "resume@example.com", "password": "ResumePass1", "name": "Resume User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _monday_of_current_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _onboard_profile(client: TestClient, token: str) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Resume User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bodyweight"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200


def test_workout_today_resumes_incomplete_session() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    first_session = plan["sessions"][0]
    exercise = first_session["exercises"][0]

    log_set = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": exercise["primary_exercise_id"],
            "exercise_id": exercise["id"],
            "set_index": 1,
            "reps": 10,
            "weight": float(exercise["recommended_working_weight"]),
        },
    )
    assert log_set.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    assert payload["session_id"] == first_session["session_id"]
    assert payload["resume"] is True
    # ensure server reports completed sets per exercise
    assert payload["exercises"][0].get("completed_sets", 0) == 1


def test_workout_today_does_not_resume_completed_session() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    first_session = plan["sessions"][0]
    for exercise in first_session["exercises"]:
        planned_sets = int(exercise.get("sets", 3))
        for set_index in range(1, planned_sets + 1):
            log_set = client.post(
                f"/workout/{first_session['session_id']}/log-set",
                headers=headers,
                json={
                    "primary_exercise_id": exercise["primary_exercise_id"],
                    "exercise_id": exercise["id"],
                    "set_index": set_index,
                    "reps": 10,
                    "weight": float(exercise["recommended_working_weight"]),
                },
            )
            assert log_set.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    assert payload["resume"] is False
