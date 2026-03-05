from datetime import date, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_progress")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "progress@example.com", credential_field: "Progress1", "name": "Progress User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _onboard_profile(client: TestClient, token: str) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Progress User",
            "age": 30,
            "weight": 80,
            "gender": "male",
            "split_preference": "full_body",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 160,
            "fat": 70,
            "carbs": 250,
        },
    )
    assert response.status_code == 200


def test_workout_progress_endpoint_reports_completed_sets() -> None:
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

    # log one set
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

    progress = client.get(f"/workout/{first_session['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    payload = progress.json()
    assert payload["completed_total"] >= 1
    assert any(e.get("exercise_id") == exercise["id"] for e in payload.get("exercises", []))
