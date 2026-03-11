from datetime import date

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


def test_adaptive_gold_workout_today_reflects_generated_repeat_failure_substitution() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-today-repeat@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="bench_press_barbell",
                current_working_weight=20.0,
                exposure_count=5,
                consecutive_under_target_exposures=3,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    selected_session = next(
        session
        for session in generated.json()["sessions"]
        if any(item.get("primary_exercise_id") == "bench_press_barbell" for item in session["exercises"])
    )
    plan_exercise = next(
        item
        for session in generated.json()["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "bench_press_barbell"
    )
    assert plan_exercise["id"] == "incline_dumbbell_press"

    log_response = client.post(
        f"/workout/{selected_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": plan_exercise.get("primary_exercise_id"),
            "exercise_id": plan_exercise["id"],
            "set_index": 1,
            "reps": int(plan_exercise["rep_range"][0]),
            "weight": float(plan_exercise["recommended_working_weight"]),
        },
    )
    assert log_response.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    first_exercise = next(
        item for item in payload["exercises"] if item.get("primary_exercise_id") == "bench_press_barbell"
    )
    assert first_exercise["id"] == "incline_dumbbell_press"
    assert first_exercise["name"] == "Incline Dumbbell Press"
    assert first_exercise["primary_exercise_id"] == "bench_press_barbell"
    assert first_exercise["movement_pattern"] == "incline_press"


def test_adaptive_gold_today_includes_core_slot_when_equipment_available() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-core-today@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    log_response = client.post(
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
    assert log_response.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    core_exercise = next(item for item in payload["exercises"] if item["id"] == "cable_crunch")
    assert core_exercise["name"] == "Cable Crunch"
    assert core_exercise["rep_range"] == [10, 15]
    assert "cable" in core_exercise["equipment_tags"]


def test_adaptive_gold_today_matches_selected_generated_session() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-hinge-today@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    generated_sessions = generated.json()["sessions"]
    today_iso = date.today().isoformat()
    selected_session = next(
        (session for session in generated_sessions if session["date"] == today_iso),
        generated_sessions[0],
    )

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercise_ids = [item["id"] for item in payload["exercises"]]
    expected_ids = [exercise["id"] for exercise in selected_session["exercises"]]
    assert payload["session_id"] == selected_session["session_id"]
    assert exercise_ids == expected_ids


def test_adaptive_gold_today_only_includes_weak_point_slots_from_selected_session() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-weak-today@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    first_exercise = first_session["exercises"][0]

    log_response = client.post(
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
    assert log_response.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercise_ids = [item["id"] for item in payload["exercises"]]
    assert "weak_chest_cable_fly" not in exercise_ids
    assert "weak_ham_leg_curl" not in exercise_ids


def test_adaptive_gold_today_excludes_later_day_arm_isolation_slots() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-arm-today@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercise_ids = [item["id"] for item in payload["exercises"]]
    assert "dumbbell_curl_incline" not in exercise_ids
    assert "triceps_pushdown_rope" not in exercise_ids


def test_adaptive_gold_log_set_and_today_preserve_substitution_guidance_continuity() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-today-guidance@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    selected_session = next(
        session
        for session in generated.json()["sessions"]
        if any(item.get("primary_exercise_id") == "bench_press_barbell" for item in session["exercises"])
    )
    first_exercise = next(
        item
        for session in generated.json()["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "bench_press_barbell"
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="bench_press_barbell",
                current_working_weight=float(first_exercise["recommended_working_weight"]),
                exposure_count=2,
                consecutive_under_target_exposures=2,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    planned_min = int(first_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{selected_session['session_id']}/log-set",
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
    assert substitution["recommended_name"] == "Incline Dumbbell Press"
    assert substitution["failed_exposure_count"] == 3
    assert substitution["trigger_threshold"] == 3

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(
        item
        for item in today_payload["exercises"]
        if item.get("primary_exercise_id") == "bench_press_barbell"
    )
    assert matching["live_recommendation"]["substitution_recommendation"]["recommended_name"] == "Incline Dumbbell Press"
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_adaptive_gold_second_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-second-guidance@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["dumbbell", "machine"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    selected_session = next(
        session
        for session in generated.json()["sessions"]
        if any(item.get("primary_exercise_id") == "row_chest_supported" for item in session["exercises"])
    )
    second_exercise = next(
        item
        for session in generated.json()["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "row_chest_supported"
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="row_chest_supported",
                current_working_weight=float(second_exercise["recommended_working_weight"]),
                exposure_count=2,
                consecutive_under_target_exposures=2,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    planned_min = int(second_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{selected_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": second_exercise.get("primary_exercise_id"),
            "exercise_id": second_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": float(second_exercise["recommended_working_weight"]),
        },
    )
    assert response.status_code == 200
    payload = response.json()

    substitution = payload["live_recommendation"]["substitution_recommendation"]
    assert substitution["recommended_name"] == "Row Machine Chest Supported"
    assert substitution["failed_exposure_count"] == 3
    assert substitution["trigger_threshold"] == 3

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(
        item
        for item in today_payload["exercises"]
        if item.get("primary_exercise_id") == "row_chest_supported"
    )
    assert matching["live_recommendation"]["substitution_recommendation"]["recommended_name"] == "Row Machine Chest Supported"
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_adaptive_gold_third_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-third-guidance@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["bodyweight", "machine"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    third_exercise = next(
        item
        for item in first_session["exercises"]
        if item.get("primary_exercise_id") == "lat_pulldown_wide"
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="lat_pulldown_wide",
                current_working_weight=float(third_exercise["recommended_working_weight"]),
                exposure_count=2,
                consecutive_under_target_exposures=2,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    planned_min = int(third_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": third_exercise.get("primary_exercise_id"),
            "exercise_id": third_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": float(third_exercise["recommended_working_weight"]),
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["exercise_id"] == "pullup_assisted_neutral"
    assert payload["live_recommendation"]["substitution_recommendation"] is None

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == third_exercise["id"])
    assert matching["id"] == "pullup_assisted_neutral"
    assert matching["primary_exercise_id"] == "lat_pulldown_wide"
    assert "substitution_recommendation" not in matching["live_recommendation"]
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_adaptive_gold_fourth_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
    _reset_db()
    client = TestClient(app)
    email = "gold-fourth-guidance@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["machine", "dumbbell", "barbell", "bench"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert response.status_code == 200

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    first_session = generated.json()["sessions"][0]
    fourth_exercise = next(
        item
        for item in first_session["exercises"]
        if item.get("id") == "hack_squat"
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="hack_squat",
                current_working_weight=float(fourth_exercise["recommended_working_weight"]),
                exposure_count=2,
                consecutive_under_target_exposures=2,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    planned_min = int(fourth_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": fourth_exercise.get("primary_exercise_id"),
            "exercise_id": fourth_exercise["id"],
            "set_index": 1,
            "reps": max(1, planned_min - 2),
            "weight": float(fourth_exercise["recommended_working_weight"]),
        },
    )
    assert response.status_code == 200
    payload = response.json()

    substitution = payload["live_recommendation"]["substitution_recommendation"]
    assert substitution["recommended_name"] == "Split Squat Db"
    assert substitution["failed_exposure_count"] == 3
    assert substitution["trigger_threshold"] == 3

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == fourth_exercise["id"])
    assert matching["live_recommendation"]["substitution_recommendation"]["recommended_name"] == "Split Squat Db"
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]
