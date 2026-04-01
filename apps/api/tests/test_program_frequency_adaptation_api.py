from datetime import date
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_frequency_adaptation_api")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, SorenessEntry, User, WorkoutPlan

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"
PHASE1_MERGED_DAY1_IDS = [
    "cross_body_lat_pull_around",
    "low_incline_smith_machine_press",
    "machine_hip_adduction",
    "leg_press",
    "lying_paused_rope_face_pull",
    "cable_crunch",
    "seated_db_shoulder_press",
    "paused_barbell_rdl",
    "chest_supported_machine_row",
    "hammer_preacher_curl",
    "cuffed_behind_the_back_lateral_raise",
    "overhead_cable_triceps_extension_bar",
]
PHASE2_MERGED_DAY1_IDS = [
    "wide_grip_pull_up",
    "flat_machine_chest_press",
    "glute_ham_raise",
    "leg_extension",
    "meadows_incline_db_lateral_raise",
    "standing_calf_raise",
    "seated_leg_curl",
    "bottom_half_smith_machine_squat",
    "chest_supported_machine_row",
    "bottom_half_seated_cable_flye",
    "machine_hip_abduction",
    "overhead_cable_triceps_extension_bar",
]


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_profile(
    client: TestClient,
    *,
    selected_program_id: str = "pure_bodybuilding_phase_1_full_body",
) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": "adaptation-api@example.com", "password": TEST_CREDENTIAL, "name": "Adapt User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Adapt User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": selected_program_id,
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bench", "barbell"],
            "weak_areas": ["chest", "hamstrings"],
            "days_available": 5,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    return headers


def test_frequency_adaptation_preview_supports_two_to_five_days() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    for days in (2, 3, 4, 5):
        response = client.post(
            "/plan/adaptation/preview",
            headers=headers,
            json={
                "target_days": days,
                "duration_weeks": 2,
                "weak_areas": ["chest", "hamstrings"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["from_days"] == 5
        assert payload["to_days"] == days
        assert payload["duration_weeks"] == 2
        assert payload["weak_areas"] == ["chest", "hamstrings"]
        assert payload["decision_trace"]["interpreter"] == "recommend_frequency_adaptation_preview"
        assert len(payload["weeks"]) == 2
        for week in payload["weeks"]:
            assert week["adapted_training_days"] == days
            assert len(week["adapted_days"]) == days


def test_frequency_adaptation_preview_uses_profile_weak_areas_when_not_provided() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={
            "target_days": 3,
            "duration_weeks": 1,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["weak_areas"] == ["chest", "hamstrings"]
    assert payload["decision_trace"]["resolved_context"]["weak_area_source"] == "profile"


def test_frequency_adaptation_preview_derives_recovery_state_and_week_index_from_user_state() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "adaptation-api@example.com").first()
        assert user is not None
        session.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=date(2026, 3, 2),
                split="full_body",
                phase="maintenance",
                payload={"mesocycle": {"week_index": 4}},
            )
        )
        session.add(
            SorenessEntry(
                user_id=user.id,
                entry_date=date(2026, 3, 7),
                severity_by_muscle={"chest": "severe", "back": "severe"},
                notes="high fatigue",
            )
        )
        session.commit()

    response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={
            "target_days": 3,
            "duration_weeks": 1,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["decision_trace"]["resolved_context"]["recovery_state"] == "high_fatigue"
    assert payload["decision_trace"]["resolved_context"]["current_week_index"] == 4
    assert payload["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_frequency_adaptation_runtime_inputs"


def test_frequency_adaptation_apply_persists_state_for_runtime_generation() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest"],
        },
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["status"] == "applied"
    assert apply_payload["target_days"] == 3
    assert apply_payload["weeks_remaining"] == 2
    assert apply_payload["decision_trace"]["interpreter"] == "interpret_frequency_adaptation_apply"

    generate_response = client.post("/plan/generate-week", headers=headers, json={})
    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert generate_payload["user"]["days_available"] == 3
    assert len(generate_payload["sessions"]) == 3
    adaptation = generate_payload.get("applied_frequency_adaptation")
    assert isinstance(adaptation, dict)
    assert adaptation["target_days"] == 3
    assert adaptation["weeks_remaining_before_apply"] == 2
    assert adaptation["weeks_remaining_after_apply"] == 1
    assert adaptation["decision_trace"]["interpreter"] == "apply_active_frequency_adaptation_runtime"


def test_frequency_adaptation_apply_completes_after_duration_weeks() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 2,
            "duration_weeks": 1,
        },
    )
    assert apply_response.status_code == 200

    first_week = client.post("/plan/generate-week", headers=headers, json={})
    assert first_week.status_code == 200
    first_payload = first_week.json()
    assert first_payload["user"]["days_available"] == 2
    adaptation = first_payload.get("applied_frequency_adaptation")
    assert isinstance(adaptation, dict)
    assert adaptation["weeks_remaining_after_apply"] == 0
    assert adaptation.get("completed") is True
    assert adaptation["decision_trace"]["outcome"]["status"] == "completed"

    second_week = client.post("/plan/generate-week", headers=headers, json={})
    assert second_week.status_code == 200
    second_payload = second_week.json()
    assert second_payload["user"]["days_available"] == 5
    assert "applied_frequency_adaptation" not in second_payload


def test_phase1_frequency_adaptation_preview_and_runtime_expose_program_specific_policy() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    preview_response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()

    preview_week = preview_payload["weeks"][0]
    assert preview_payload["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert preview_week["program_policy"] == "pure_bodybuilding_phase_1_full_body_5_to_3"
    assert preview_week["week_label"] == "Week 1"
    assert preview_week["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert preview_week["adapted_days"][0]["day_name"] == "Full Body #1 + Full Body #2"
    assert preview_week["adapted_days"][1]["day_name"] == "Full Body #3 + Full Body #4"
    assert preview_week["adapted_days"][2]["day_name"] == "Arms & Weak Points"
    assert preview_week["adapted_days"][0]["exercise_ids"] == PHASE1_MERGED_DAY1_IDS
    assert preview_payload["decision_trace"]["outcome"]["policy_mode"] == "program_specific"
    assert preview_payload["decision_trace"]["outcome"]["policy_id"] == "pure_bodybuilding_phase_1_full_body_5_to_3"

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert apply_response.status_code == 200

    generate_response = client.post("/plan/generate-week", headers=headers, json={})
    assert generate_response.status_code == 200
    generate_payload = generate_response.json()

    adaptation = generate_payload["applied_frequency_adaptation"]
    assert adaptation["policy_mode"] == "program_specific"
    assert adaptation["policy_id"] == "pure_bodybuilding_phase_1_full_body_5_to_3"
    assert adaptation["preservation_focus"] == [
        "full_body_intent",
        "weak_point_intent",
        "progression_continuity",
    ]
    assert adaptation["decision_trace"]["source_trace"]["preview_trace"]["outcome"]["policy_id"] == (
        "pure_bodybuilding_phase_1_full_body_5_to_3"
    )


def test_phase2_frequency_adaptation_preview_and_runtime_expose_program_specific_policy() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client, selected_program_id="pure_bodybuilding_phase_2_full_body")

    preview_response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_2_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()

    preview_week = preview_payload["weeks"][0]
    assert preview_payload["program_id"] == "pure_bodybuilding_phase_2_full_body"
    assert preview_week["program_policy"] == "pure_bodybuilding_phase_2_full_body_5_to_3"
    assert preview_week["week_label"] == "Week 1"
    assert preview_week["adapted_days"][0]["day_name"] == "Full Body #1 + Full Body #2"
    assert preview_week["adapted_days"][1]["day_name"] == "Full Body #3 + Full Body #4"
    assert preview_week["adapted_days"][2]["day_name"] == "Arms & Weak Points"
    assert preview_week["adapted_days"][0]["exercise_ids"] == PHASE2_MERGED_DAY1_IDS
    assert preview_payload["decision_trace"]["outcome"]["policy_mode"] == "program_specific"
    assert preview_payload["decision_trace"]["outcome"]["policy_id"] == "pure_bodybuilding_phase_2_full_body_5_to_3"

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_2_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert apply_response.status_code == 200

    generate_response = client.post("/plan/generate-week", headers=headers, json={})
    assert generate_response.status_code == 200
    generate_payload = generate_response.json()

    adaptation = generate_payload["applied_frequency_adaptation"]
    assert adaptation["policy_mode"] == "program_specific"
    assert adaptation["policy_id"] == "pure_bodybuilding_phase_2_full_body_5_to_3"
    assert adaptation["decision_trace"]["source_trace"]["preview_trace"]["outcome"]["policy_id"] == (
        "pure_bodybuilding_phase_2_full_body_5_to_3"
    )


def test_frequency_adaptation_preserves_progression_state_across_5_to_3_to_5_windows() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 1,
            "weak_areas": ["chest"],
        },
    )
    assert apply_response.status_code == 200

    week_one = client.post("/plan/generate-week", headers=headers, json={})
    assert week_one.status_code == 200
    week_one_payload = week_one.json()
    assert week_one_payload["user"]["days_available"] == 3

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    first_exercise = today_payload["exercises"][0]
    primary_id = first_exercise.get("primary_exercise_id") or first_exercise["id"]

    log_set = client.post(
        f"/workout/{today_payload['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": int(first_exercise["rep_range"][0]),
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert log_set.status_code == 200

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "adaptation-api@example.com").first()
        assert user is not None
        state = (
            session.query(ExerciseState)
            .filter(ExerciseState.user_id == user.id, ExerciseState.exercise_id == str(primary_id))
            .first()
        )
        assert state is not None
        assert float(state.current_working_weight) > 0

    week_two = client.post("/plan/generate-week", headers=headers, json={})
    assert week_two.status_code == 200
    week_two_payload = week_two.json()
    assert week_two_payload["user"]["days_available"] == 5
    assert "applied_frequency_adaptation" not in week_two_payload

    training_state = client.get("/profile/training-state", headers=headers)
    assert training_state.status_code == 200
    progression_ids = {
        str(item.get("exercise_id"))
        for item in training_state.json().get("progression_state_per_exercise", [])
        if item.get("exercise_id")
    }
    assert str(primary_id) in progression_ids


def test_frequency_adaptation_preview_returns_precise_duration_validation_message() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 10,
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(entry["msg"] == "Value error, Temporary duration must be between 1 and 8 weeks." for entry in detail)
