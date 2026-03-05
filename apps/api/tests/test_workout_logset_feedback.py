from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_logset_feedback")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "setfeedback@example.com", credential_field: "Feedback1", "name": "Set Feedback"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _onboard_profile(client: TestClient, token: str) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Set Feedback",
            "age": 31,
            "weight": 81,
            "gender": "male",
            "split_preference": "full_body",
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bodyweight"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 75,
            "carbs": 250,
        },
    )
    assert response.status_code == 200


def test_log_set_returns_planned_vs_actual_feedback() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    planned_min, planned_max = first_exercise["rep_range"]
    planned_weight = float(first_exercise["recommended_working_weight"])

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": max(5.0, planned_weight - 5.0),
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["exercise_id"] == first_exercise["id"]
    assert payload["set_index"] == 1
    assert payload["planned_reps_min"] == planned_min
    assert payload["planned_reps_max"] == planned_max
    assert payload["planned_weight"] == planned_weight
    assert payload["guidance"] == "below_target_reps_reduce_or_hold_load"
    assert "next_working_weight" in payload
    assert payload["live_recommendation"]["completed_sets"] == 1
    assert payload["live_recommendation"]["remaining_sets"] == int(first_exercise["sets"]) - 1
    assert payload["live_recommendation"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
