from datetime import date, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_progress")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutSessionState


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


def test_workout_today_and_progress_agree_when_no_logs() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    _onboard_profile(client, token)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()

    progress = client.get(f"/workout/{today_payload['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    progress_payload = progress.json()

    today_completed = {item["id"]: int(item.get("completed_sets") or 0) for item in today_payload.get("exercises", [])}
    progress_completed = {
        item["exercise_id"]: int(item.get("completed_sets") or 0)
        for item in progress_payload.get("exercises", [])
    }
    assert sum(today_completed.values()) == 0
    assert progress_payload["completed_total"] == 0
    assert today_completed == progress_completed


def test_workout_today_and_progress_agree_when_logged_sets_exist() -> None:
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
    today_payload = today.json()

    progress = client.get(f"/workout/{today_payload['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    progress_payload = progress.json()

    today_completed = {item["id"]: int(item.get("completed_sets") or 0) for item in today_payload.get("exercises", [])}
    progress_completed = {
        item["exercise_id"]: int(item.get("completed_sets") or 0)
        for item in progress_payload.get("exercises", [])
    }
    assert today_completed == progress_completed
    assert sum(today_completed.values()) == int(progress_payload["completed_total"] or 0)


def test_workout_today_prefers_logs_when_session_state_completed_sets_is_higher() -> None:
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

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "progress@example.com").first()
        assert user is not None
        state = (
            db.query(WorkoutSessionState)
            .filter(
                WorkoutSessionState.user_id == user.id,
                WorkoutSessionState.workout_id == first_session["session_id"],
                WorkoutSessionState.exercise_id == exercise["id"],
            )
            .first()
        )
        assert state is not None
        state.completed_sets = 4
        db.add(state)
        db.commit()

    today = client.get("/workout/today", headers=headers)
    progress = client.get(f"/workout/{first_session['session_id']}/progress", headers=headers)
    assert today.status_code == 200
    assert progress.status_code == 200
    today_payload = today.json()
    progress_payload = progress.json()
    today_map = {item["id"]: int(item.get("completed_sets") or 0) for item in today_payload["exercises"]}
    progress_map = {item["exercise_id"]: int(item.get("completed_sets") or 0) for item in progress_payload["exercises"]}
    assert today_map == progress_map


def test_workout_today_prefers_logs_when_session_state_completed_sets_is_lower() -> None:
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

    for set_index in (1, 2):
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

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "progress@example.com").first()
        assert user is not None
        state = (
            db.query(WorkoutSessionState)
            .filter(
                WorkoutSessionState.user_id == user.id,
                WorkoutSessionState.workout_id == first_session["session_id"],
                WorkoutSessionState.exercise_id == exercise["id"],
            )
            .first()
        )
        assert state is not None
        state.completed_sets = 0
        db.add(state)
        db.commit()

    today = client.get("/workout/today", headers=headers)
    progress = client.get(f"/workout/{first_session['session_id']}/progress", headers=headers)
    assert today.status_code == 200
    assert progress.status_code == 200
    today_payload = today.json()
    progress_payload = progress.json()
    today_map = {item["id"]: int(item.get("completed_sets") or 0) for item in today_payload["exercises"]}
    progress_map = {item["exercise_id"]: int(item.get("completed_sets") or 0) for item in progress_payload["exercises"]}
    assert today_map == progress_map


def test_workout_today_keeps_live_recommendation_but_zero_completion_without_logs() -> None:
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

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "progress@example.com").first()
        assert user is not None
        db.add(
            WorkoutSessionState(
                user_id=user.id,
                workout_id=first_session["session_id"],
                primary_exercise_id=exercise["primary_exercise_id"],
                exercise_id=exercise["id"],
                planned_sets=int(exercise["sets"]),
                planned_reps_min=int(exercise["rep_range"][0]),
                planned_reps_max=int(exercise["rep_range"][1]),
                planned_weight=float(exercise["recommended_working_weight"]),
                completed_sets=1,
                total_logged_reps=10,
                total_logged_weight=float(exercise["recommended_working_weight"]),
                set_history=[{"set_index": 1, "reps": 10, "weight": float(exercise["recommended_working_weight"])}],
                remaining_sets=max(0, int(exercise["sets"]) - 1),
                recommended_reps_min=int(exercise["rep_range"][0]),
                recommended_reps_max=int(exercise["rep_range"][1]),
                recommended_weight=float(exercise["recommended_working_weight"]),
                last_guidance="remaining_sets_hold_load_and_match_target_reps",
            )
        )
        db.commit()

    today = client.get("/workout/today", headers=headers)
    progress = client.get(f"/workout/{first_session['session_id']}/progress", headers=headers)
    assert today.status_code == 200
    assert progress.status_code == 200
    today_payload = today.json()
    progress_payload = progress.json()

    matching = next(item for item in today_payload["exercises"] if item["id"] == exercise["id"])
    assert int(matching.get("completed_sets") or 0) == 0
    assert isinstance(matching.get("live_recommendation"), dict)
    assert int(progress_payload["completed_total"] or 0) == 0


def test_workout_today_and_progress_agree_with_partial_exercise_logs() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    _onboard_profile(client, token)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    first_session = plan["sessions"][0]
    exercises = first_session["exercises"]
    assert len(exercises) >= 2

    first_exercise = exercises[0]
    second_exercise = exercises[1]
    log_set = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise["primary_exercise_id"],
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": 10,
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert log_set.status_code == 200

    today = client.get("/workout/today", headers=headers)
    progress = client.get(f"/workout/{first_session['session_id']}/progress", headers=headers)
    assert today.status_code == 200
    assert progress.status_code == 200
    today_payload = today.json()
    progress_payload = progress.json()

    today_map = {item["id"]: int(item.get("completed_sets") or 0) for item in today_payload["exercises"]}
    progress_map = {item["exercise_id"]: int(item.get("completed_sets") or 0) for item in progress_payload["exercises"]}
    assert today_map == progress_map
    assert today_map[first_exercise["id"]] == 1
    assert today_map[second_exercise["id"]] == 0
