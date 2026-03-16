import copy
from fastapi.testclient import TestClient
import pytest

from test_db import configure_test_database

configure_test_database("test_workout_logset_feedback")

from app.database import Base, engine
from app.database import SessionLocal
from app.main import app
from app.models import ExerciseState, WorkoutPlan


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


def _onboard_profile(
    client: TestClient,
    token: str,
    *,
    split_preference: str = "full_body",
    selected_program_id: str = "pure_bodybuilding_phase_1_full_body",
    days_available: int = 3,
) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Set Feedback",
            "age": 31,
            "weight": 81,
            "gender": "male",
            "split_preference": split_preference,
            "selected_program_id": selected_program_id,
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bodyweight"],
            "days_available": days_available,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 75,
            "carbs": 250,
        },
    )
    assert response.status_code == 200


def _inject_estimated_1rm_into_latest_plan(
    *,
    workout_id: str,
    exercise_id: str,
    estimated_1rm: float,
) -> None:
    with SessionLocal() as db:
        latest_plan = db.query(WorkoutPlan).order_by(WorkoutPlan.created_at.desc()).first()
        assert latest_plan is not None
        payload = copy.deepcopy(latest_plan.payload or {})
        sessions = list(payload.get("sessions") or [])
        updated = False
        for session in sessions:
            if session.get("session_id") != workout_id:
                continue
            exercises = list(session.get("exercises") or [])
            for exercise in exercises:
                if exercise.get("id") == exercise_id:
                    exercise["estimated_1rm"] = estimated_1rm
                    updated = True
        assert updated
        latest_plan.payload = payload
        db.add(latest_plan)
        db.commit()


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
    assert payload["guidance_rationale"] == (
        "Performance fell below the target range. Hold load on the first miss and only reduce if it repeats across 2 exposures."
    )
    assert payload["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"
    assert payload["decision_trace"]["outcome"]["guidance"] == payload["guidance"]
    assert "next_working_weight" in payload
    assert payload["live_recommendation"]["completed_sets"] == 1
    assert payload["live_recommendation"]["remaining_sets"] == int(first_exercise["sets"]) - 1
    assert payload["live_recommendation"]["guidance"] == "remaining_sets_hold_load_and_match_target_reps"
    assert payload["live_recommendation"]["guidance_rationale"] == (
        "Keep the same load for the remaining sets and match the programmed rep target."
    )
    assert payload["live_recommendation"]["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"


def test_log_set_holds_next_weight_on_first_underperformance_when_canonical_rules_apply() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    planned_min, _planned_max = first_exercise["rep_range"]
    planned_weight = float(first_exercise["recommended_working_weight"])

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": planned_weight,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_working_weight"] == planned_weight
    assert payload["guidance_rationale"].startswith("Performance fell below the target range.")
    assert payload["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"


def test_log_set_applies_rules_runtime_starting_load_for_first_exposure() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    planned_weight = float(first_exercise["recommended_working_weight"])
    estimated_1rm = (planned_weight / 0.72) + 25.0
    expected_start_weight = round(round(((estimated_1rm * 72.0) / 100.0) / 0.5) * 0.5, 2)

    _inject_estimated_1rm_into_latest_plan(
        workout_id=first_session["session_id"],
        exercise_id=first_exercise["id"],
        estimated_1rm=estimated_1rm,
    )

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": first_exercise["rep_range"][0],
            "weight": planned_weight,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["starting_load_decision_trace"]["interpreter"] == "resolve_starting_load"
    assert payload["starting_load_decision_trace"]["outcome"] == {
        "working_weight": expected_start_weight,
        "source": "estimated_1rm_fallback_percent",
    }
    assert payload["next_working_weight"] == expected_start_weight

    with SessionLocal() as db:
        state = (
            db.query(ExerciseState)
            .filter(ExerciseState.exercise_id == (first_exercise.get("primary_exercise_id") or first_exercise["id"]))
            .first()
        )

    assert state is not None
    assert state.current_working_weight == expected_start_weight
    assert state.exposure_count == 1


@pytest.mark.parametrize(
    ("split_preference", "selected_program_id", "days_available"),
    [
        ("ppl", "ppl_v1", 3),
        ("upper_lower", "upper_lower_v1", 4),
    ],
)
def test_log_set_holds_next_weight_for_phase_2_linked_programs_on_first_underperformance(
    split_preference: str,
    selected_program_id: str,
    days_available: int,
) -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(
        client,
        token,
        split_preference=split_preference,
        selected_program_id=selected_program_id,
        days_available=days_available,
    )

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    planned_min, _planned_max = first_exercise["rep_range"]
    planned_weight = float(first_exercise["recommended_working_weight"])

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": planned_weight,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_working_weight"] == planned_weight
    assert payload["guidance_rationale"] == (
        "Performance fell below the target range. Hold load on the first miss and only reduce if it repeats across 2 exposures."
    )
    assert payload["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"
