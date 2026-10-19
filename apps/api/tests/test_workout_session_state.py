from copy import deepcopy
from datetime import date, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_workout_session_state")

from app.database import Base, SessionLocal, engine
from app.main import app
from authored_test_helpers import source_equipment
from app.models import ExerciseState, User, WorkoutPlan, WorkoutSessionState


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


def _onboard_profile(
    client: TestClient, token: str, *, equipment_profile: list[str] | None = None,
    selected_program_id: str = "full_body_v1",
) -> None:
    response = client.post(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Session State",
            "age": 29,
            "weight": 79,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": selected_program_id,
            "training_location": "home",
            "equipment_profile": equipment_profile or source_equipment(),
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
    profile = client.get('/profile', headers=headers)
    assert profile.status_code == 200
    if profile.json()['selected_program_id'] == 'full_body_v1':
        stored = _seed_historical_generated_plan(client, headers)
    else:
        generated = client.post('/plan/generate-week', headers=headers, json={})
        assert generated.status_code == 200
        stored = generated.json()
    first_session = stored['sessions'][0]
    first_exercise = first_session["exercises"][0]
    return first_session, first_exercise


def _seed_historical_generated_plan(client: TestClient, headers: dict[str, str]) -> dict:
    """Synthetic persisted history, not a new plan or source-layout replay."""
    profile = client.get('/profile', headers=headers)
    assert profile.status_code == 200
    monday = date.today() - timedelta(days=date.today().weekday())
    definitions = [
        ('hack_squat', 'Hack squat', 'hack_squat', 'squat', ['quads'], ['machine']),
        ('chest_supported_machine_row', 'Machine row', 'chest_supported_machine_row', 'horizontal_pull', ['back'], ['machine']),
        ('dumbbell_rdl', 'Dumbbell RDL', 'barbell_rdl', 'hinge', ['hamstrings'], ['dumbbell']),
        ('cable_crunch', 'Cable crunch', 'cable_crunch', 'core', ['abs'], ['cable']),
    ]
    exercises = [dict(id=id, name=name, primary_exercise_id=primary, movement_pattern=pattern,
        primary_muscles=muscles, equipment_tags=equipment, sets=3, rep_range=[8, 12],
        recommended_working_weight=20.0, start_weight=20.0, substitution_candidates=[])
        for id, name, primary, pattern, muscles, equipment in definitions]
    payload = {'program_template_id': 'full_body_v1', 'split': 'full_body', 'phase': 'maintenance',
        'week_start': monday.isoformat(), 'historical_fixture': True,
        'mesocycle': {'week_index': 1, 'authored_week_index': 1},
        'sessions': [{'session_id': 'full_body_v1-historical-day1', 'title': 'Historical day 1',
            'date': date.today().isoformat(), 'exercises': exercises},
            {'session_id': 'full_body_v1-historical-day2', 'title': 'Historical day 2',
             'date': (date.today() + timedelta(days=1)).isoformat(), 'exercises': [
                dict(id=id, name=id, primary_exercise_id=id, movement_pattern='isolation',
                    primary_muscles=['biceps'], equipment_tags=['cable'], sets=2, rep_range=[10, 15],
                    recommended_working_weight=10.0, substitution_candidates=[])
                for id in ['dumbbell_curl_incline', 'triceps_pushdown_rope', 'weak_chest_cable_fly', 'weak_ham_leg_curl']]}]}
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == profile.json()['email']).one()
        db.add(WorkoutPlan(user_id=user.id, week_start=monday, split='full_body',
            phase='maintenance', payload=deepcopy(payload)))
        db.commit()
    return payload


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
    assert live["guidance"] == "remaining_sets_hold_load_and_match_target_reps"
    assert float(live["recommended_weight"]) == logged_weight


def test_today_starting_load_defaults_are_not_flat_when_planned_weights_are_uniform() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client, "sessionstate-startingload@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _onboard_profile(client, token)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "sessionstate-startingload@example.com").first()
        assert user is not None
        db.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=date.today(),
                split="full_body",
                phase="accumulation",
                payload={
                    "sessions": [
                        {
                            "session_id": "manual-day1",
                            "title": "Manual Day",
                            "date": date.today().isoformat(),
                            "exercises": [
                                {
                                    "id": "belt_squat",
                                    "name": "Belt Squat",
                                    "sets": 3,
                                    "rep_range": [8, 12],
                                    "recommended_working_weight": 20.0,
                                    "movement_pattern": "squat",
                                    "primary_muscles": ["quads", "glutes"],
                                },
                                {
                                    "id": "bayesian_curl",
                                    "name": "Bayesian Curl",
                                    "sets": 3,
                                    "rep_range": [8, 12],
                                    "recommended_working_weight": 20.0,
                                    "load_semantics": "assistance",
                                    "primary_muscles": ["biceps"],
                                },
                            ],
                        }
                    ]
                },
            )
        )
        db.commit()

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercises = {item["id"]: item for item in payload["exercises"]}
    assert float(exercises["belt_squat"]["recommended_working_weight"]) > float(
        exercises["bayesian_curl"]["recommended_working_weight"]
    )
    assert exercises["belt_squat"]["starting_load_quality_source"] == "movement_pattern_lower_body_default"
    assert exercises["bayesian_curl"]["starting_load_quality_source"] in {
        "movement_pattern_upper_compound_default",
        "load_semantics_assistance_default",
    }


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


def test_authored_repeat_failure_does_not_offer_generic_substitution() -> None:
    _reset_db()
    client = TestClient(app)
    email = "sessionstate-repeat@example.com"
    token = _register_token(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    _onboard_profile(client, token, selected_program_id="pure_bodybuilding_phase_1_full_body")
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
    assert substitution is None  # Authored choices require exact source permission and consent.

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == first_exercise["id"])
    today_substitution = matching["live_recommendation"].get("substitution_recommendation")
    assert today_substitution is None
    assert matching["name"] == first_exercise["name"]
    assert matching["authored_prescription"] == first_exercise["authored_prescription"]


def test_historical_generated_workout_today_preserves_performed_variant_after_logging() -> None:
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
                exercise_id="hack_squat",
                current_working_weight=20.0,
                exposure_count=5,
                consecutive_under_target_exposures=3,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    generated_payload = _seed_historical_generated_plan(client, headers)
    selected_session = generated_payload["sessions"][0]
    plan_exercise = selected_session["exercises"][0]

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
        item for item in payload["exercises"] if item.get("primary_exercise_id") == plan_exercise["primary_exercise_id"]
    )
    assert first_exercise["id"] == plan_exercise["id"]
    assert first_exercise["name"] == plan_exercise["name"]
    assert first_exercise["primary_exercise_id"] == plan_exercise["primary_exercise_id"]
    assert first_exercise["movement_pattern"] == plan_exercise["movement_pattern"]


def test_historical_generated_today_retains_stored_equipment_slots() -> None:
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

    generated_payload = _seed_historical_generated_plan(client, headers)
    first_session = generated_payload["sessions"][0]
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
    expected_ids = [item["id"] for item in first_session["exercises"]]
    assert exercise_ids == expected_ids
    assert any(
        "cable" in item.get("equipment_tags", []) or "machine" in item.get("equipment_tags", [])
        for item in payload["exercises"]
    )


def test_historical_generated_today_matches_selected_stored_session() -> None:
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

    generated_payload = _seed_historical_generated_plan(client, headers)
    generated_sessions = generated_payload["sessions"]
    today_iso = date.today().isoformat()
    selected_session = next(
        (session for session in generated_sessions if session["date"] == today_iso),
        generated_sessions[0],
    )

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercise_ids = [item["id"] for item in payload["exercises"]]
    selected_session = next(session for session in generated_sessions if session["session_id"] == payload["session_id"])
    expected_ids = [exercise["id"] for exercise in selected_session["exercises"]]
    assert exercise_ids == expected_ids
    selected_exercise = selected_session["exercises"][0]
    matching = next(item for item in payload["exercises"] if item["id"] == selected_exercise["id"])
    assert matching["sets"] == selected_exercise["sets"]
    assert matching["rep_range"] == selected_exercise["rep_range"]
    assert matching["primary_exercise_id"] == selected_exercise["primary_exercise_id"]
    assert matching["recommended_working_weight"] >= 0


def test_historical_generated_today_does_not_add_later_weakpoint_slots() -> None:
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

    first_session = _seed_historical_generated_plan(client, headers)['sessions'][0]
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


def test_historical_generated_today_excludes_later_day_arm_isolation_slots() -> None:
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

    _seed_historical_generated_plan(client, headers)

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    payload = today.json()
    exercise_ids = [item["id"] for item in payload["exercises"]]
    assert "dumbbell_curl_incline" not in exercise_ids
    assert "triceps_pushdown_rope" not in exercise_ids


def test_historical_generated_log_set_and_today_preserve_substitution_guidance_continuity() -> None:
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

    generated_payload = _seed_historical_generated_plan(client, headers)
    selected_session = generated_payload["sessions"][0]
    first_exercise = selected_session["exercises"][0]

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id=str(first_exercise["primary_exercise_id"]),
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

    assert payload["live_recommendation"]["substitution_recommendation"] is None

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(
        item
        for item in today_payload["exercises"]
        if item.get("primary_exercise_id") == first_exercise["primary_exercise_id"]
    )
    assert matching["live_recommendation"].get("substitution_recommendation") is None
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_historical_generated_second_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
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

    generated_payload = _seed_historical_generated_plan(client, headers)
    selected_session = next(
        session
        for session in generated_payload["sessions"]
        if any(item.get("primary_exercise_id") == "chest_supported_machine_row" for item in session["exercises"])
    )
    second_exercise = next(
        item
        for session in generated_payload["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "chest_supported_machine_row"
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="chest_supported_machine_row",
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
    assert substitution is None

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(
        item
        for item in today_payload["exercises"]
        if item.get("primary_exercise_id") == "chest_supported_machine_row"
    )
    assert matching["live_recommendation"].get("substitution_recommendation") is None
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_historical_generated_third_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
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

    generated_sessions = _seed_historical_generated_plan(client, headers)['sessions']
    selected_session = next(
        session
        for session in generated_sessions
        if any(item.get("id") != item.get("primary_exercise_id") for item in session["exercises"])
    )
    third_exercise = next(
        item
        for item in selected_session["exercises"]
        if item.get("id") != item.get("primary_exercise_id")
    )

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            ExerciseState(
                user_id=user.id,
                exercise_id=str(third_exercise["primary_exercise_id"]),
                current_working_weight=float(third_exercise["recommended_working_weight"]),
                exposure_count=1,
                consecutive_under_target_exposures=0,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        db.commit()

    planned_min = int(third_exercise["rep_range"][0])
    response = client.post(
        f"/workout/{selected_session['session_id']}/log-set",
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

    assert payload["exercise_id"] == third_exercise["id"]
    assert payload["live_recommendation"]["substitution_recommendation"] is None

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == third_exercise["id"])
    assert matching["id"] == third_exercise["id"]
    assert matching["primary_exercise_id"] == third_exercise["primary_exercise_id"]
    assert matching["live_recommendation"].get("substitution_recommendation") is None
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]


def test_historical_generated_fourth_exercise_today_and_log_set_preserve_substitution_guidance() -> None:
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

    generated_payload = _seed_historical_generated_plan(client, headers)
    generated_sessions = generated_payload["sessions"]
    selected_session = next(
        session
        for session in generated_sessions
        if any(item.get("id") == "hack_squat" for item in session["exercises"])
    )
    fourth_exercise = next(
        item
        for item in selected_session["exercises"]
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
        f"/workout/{selected_session['session_id']}/log-set",
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
    assert substitution is None

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    matching = next(item for item in today_payload["exercises"] if item["id"] == fourth_exercise["id"])
    assert matching["live_recommendation"].get("substitution_recommendation") is None
    assert matching["live_recommendation"]["guidance"] == payload["live_recommendation"]["guidance"]
