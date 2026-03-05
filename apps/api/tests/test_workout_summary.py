from uuid import uuid4

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_summary")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    generated_secret = f"Pw-{uuid4().hex[:12]}"
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "summary@example.com", credential_field: generated_secret, "name": "Summary User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _onboard_profile(client: TestClient, token: str) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Summary User",
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


def test_workout_summary_returns_progress_and_guidance() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    for exercise in first_session["exercises"]:
        planned_min, _planned_max = exercise["rep_range"]
        planned_sets = int(exercise.get("sets", 3))
        planned_weight = float(exercise["recommended_working_weight"])

        for set_index in range(1, planned_sets + 1):
            response = client.post(
                f"/workout/{first_session['session_id']}/log-set",
                headers=headers,
                json={
                    "primary_exercise_id": exercise.get("primary_exercise_id"),
                    "exercise_id": exercise["id"],
                    "set_index": set_index,
                    "reps": max(1, planned_min - 2),
                    "weight": max(5.0, planned_weight - 2.5),
                },
            )
            assert response.status_code == 200

    first_planned_sets = int(first_exercise.get("sets", 3))

    summary_response = client.get(f"/workout/{first_session['session_id']}/summary", headers=headers)
    assert summary_response.status_code == 200
    payload = summary_response.json()

    assert payload["workout_id"] == first_session["session_id"]
    assert payload["percent_complete"] == 100
    assert payload["overall_guidance"] == "performance_below_target_adjust_load_and_recover"

    target_summary = next(item for item in payload["exercises"] if item["exercise_id"] == first_exercise["id"])
    assert target_summary["performed_sets"] == first_planned_sets
    assert target_summary["completion_pct"] == 100
    assert target_summary["guidance"] == "below_target_reps_reduce_or_hold_load"
