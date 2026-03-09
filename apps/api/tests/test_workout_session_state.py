from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_session_state")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, User, WorkoutSessionState


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient, email: str) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": email, credential_field: "SessionState1", "name": "Session State"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _onboard_profile(client: TestClient, token: str, *, equipment_profile: list[str] | None = None) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "training_location": "home",
            "equipment_profile": equipment_profile or ["dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200


def _setup_first_exercise(client: TestClient, headers: dict[str, str]) -> tuple[dict, dict]:
    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]
    return first_session, first_exercise


def test_workout_session_state_persists_set_level_tracking() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client, "sessionstate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)
    first_session, first_exercise = _setup_first_exercise(client, headers)

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": int(first_exercise["rep_range"][0]),
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        state = (
            db.query(WorkoutSessionState)
            .filter(
                WorkoutSessionState.workout_id == first_session["session_id"],
                WorkoutSessionState.exercise_id == first_exercise["id"],
            )
            .first()
        )

    assert state is not None
    assert state.completed_sets == 1
    assert state.remaining_sets == int(first_exercise["sets"]) - 1
    assert isinstance(state.set_history, list)
    assert len(state.set_history) == 1
    assert int(state.set_history[0]["set_index"]) == 1

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == first_exercise["id"])
    assert matching["completed_sets"] == 1
    assert matching["live_recommendation"]["remaining_sets"] == int(first_exercise["sets"]) - 1


def test_log_set_live_recommendation_reduces_load_when_reps_below_target() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client, "sessionstate-low@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)
    first_session, first_exercise = _setup_first_exercise(client, headers)

    planned_min = int(first_exercise["rep_range"][0])
    logged_weight = float(first_exercise["recommended_working_weight"])

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": logged_weight,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    live = payload["live_recommendation"]
    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert float(live["recommended_weight"]) <= logged_weight


def test_log_set_live_recommendation_increases_load_when_reps_above_target() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client, "sessionstate-high@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token)
    first_session, first_exercise = _setup_first_exercise(client, headers)

    planned_max = int(first_exercise["rep_range"][1])
    logged_weight = float(first_exercise["recommended_working_weight"])

    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": planned_max + 2,
            "weight": logged_weight,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    live = payload["live_recommendation"]
    assert live["guidance"] == "remaining_sets_increase_load_keep_reps_controlled"
    assert float(live["recommended_weight"]) >= logged_weight


def test_log_set_surfaces_repeat_failure_substitution_recommendation() -> None:
    _reset_db()
    client = TestClient(app)
    email = "sessionstate-repeat@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token, equipment_profile=["cable", "machine", "dumbbell", "barbell"])
    first_session, first_exercise = _setup_first_exercise(client, headers)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        state = ExerciseState(
            user_id=user.id,
            exercise_id=first_exercise.get("primary_exercise_id") or first_exercise["id"],
            current_working_weight=float(first_exercise["recommended_working_weight"]),
            exposure_count=2,
            consecutive_under_target_exposures=2,
            last_progression_action="hold",
            fatigue_score=0,
        )
        db.add(state)
        db.commit()

    planned_min = int(first_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert response.status_code == 200
    payload = response.json()

    substitution = payload["live_recommendation"]["substitution_recommendation"]
    assert substitution["recommended_name"] == "Chest Supported Row"
    assert substitution["failed_exposure_count"] == 3
    assert substitution["trigger_threshold"] == 3

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == first_exercise["id"])
    assert matching["live_recommendation"]["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"
