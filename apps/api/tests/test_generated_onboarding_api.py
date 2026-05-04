from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_generated_onboarding_api")

from app.database import Base, engine
from app.database import SessionLocal
from app.main import app
from app.models import User, WorkoutPlan, WorkoutSetLog
from app.routers import plan as plan_router


TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_user(client: TestClient, *, email: str, name: str) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": email, "password": TEST_CREDENTIAL, "name": name},
    )
    assert register.status_code == 200
    return {"Authorization": f"Bearer {register.json()['access_token']}"}


def _post_profile(
    client: TestClient,
    *,
    headers: dict[str, str],
    selected_program_id: str,
    split_preference: str,
    days_available: int,
) -> None:
    payload = {
        "name": "Generated Onboarding User",
        "age": 30,
        "weight": 82,
        "gender": "male",
        "split_preference": split_preference,
        "selected_program_id": selected_program_id,
        "program_selection_mode": "manual",
        "training_location": "gym",
        "equipment_profile": ["barbell", "bench", "dumbbell", "machine"],
        "weak_areas": ["chest"],
        "days_available": days_available,
        "nutrition_phase": "maintenance",
        "calories": 2600,
        "protein": 180,
        "fat": 70,
        "carbs": 280,
        "onboarding_answers": {},
    }
    response = client.post("/profile", headers=headers, json=payload)
    assert response.status_code == 200


def _generated_onboarding_payload() -> dict:
    return {
        "generated_onboarding": {
            "goal_mode": "hypertrophy",
            "target_days": 4,
            "session_time_band_source": "30_45",
            "training_status": "advanced",
            "trained_consistently_last_4_weeks": True,
            "equipment_pool": ["barbell", "bench", "dumbbell", "machine"],
            "movement_restrictions": ["overhead_pressing"],
            "recovery_modifier": "high",
            "weakpoint_targets": ["back", "delts"],
            "preference_bias": "mixed",
            "height_cm": 180,
            "bodyweight_kg": 85,
            "bodyweight_exercise_comfort": "comfortable",
            "disliked_tags": {
                "disliked_exercises": ["barbell_back_squat"],
                "disliked_equipment": ["bands"],
            },
        },
        "mark_complete": True,
    }


def test_generated_onboarding_upsert_is_non_destructive_with_existing_plan_and_logs() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-nondestructive@example.com", name="Generated Onboarding Non-Destructive")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "generated-onboarding-nondestructive@example.com").first()
        assert user is not None
        session.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=date.today(),
                split="full_body",
                phase="hypertrophy",
                payload={"sessions": []},
            )
        )
        session.add(
            WorkoutSetLog(
                user_id=user.id,
                workout_id="session-1",
                primary_exercise_id="bench_press",
                exercise_id="bench_press",
                set_index=1,
                reps=8,
                weight=80.0,
                rpe=8.0,
                set_kind="work",
                parent_set_index=None,
                technique=None,
            )
        )
        session.commit()
        before_plan_count = session.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count()
        before_log_count = session.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user.id).count()

    response = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert response.status_code == 200

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "generated-onboarding-nondestructive@example.com").first()
        assert user is not None
        after_plan_count = session.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count()
        after_log_count = session.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user.id).count()

    assert after_plan_count == before_plan_count
    assert after_log_count == before_log_count


def test_generated_onboarding_get_returns_saved_payload_and_metadata() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-get@example.com", name="Generated Onboarding Get")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    save = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert save.status_code == 200

    get = client.get("/profile/generated-onboarding", headers=headers)
    assert get.status_code == 200
    payload = get.json()
    assert payload["generated_onboarding_version"] == "v1"
    assert payload["generated_onboarding_complete"] is True
    assert payload["profile_completeness"] == "high"
    assert payload["generated_onboarding"]["goal_mode"] == "hypertrophy"
    assert payload["generated_onboarding"]["equipment_pool"] == ["barbell", "bench", "dumbbell", "machine"]
    assert payload["missing_fields"] == []

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "generated-onboarding-get@example.com").first()
        assert user is not None
        onboarding_answers = dict(user.onboarding_answers or {})
        saved_state = dict(onboarding_answers.get("generated_onboarding") or {})
        saved_payload = dict(saved_state.get("generated_onboarding") or {})
    assert saved_state.get("generated_onboarding_complete") is True
    assert saved_state.get("generated_onboarding_version") == "v1"
    assert saved_payload.get("goal_mode") == "hypertrophy"
    assert saved_payload.get("equipment_pool") == ["barbell", "bench", "dumbbell", "machine"]


def test_generated_onboarding_invalid_values_are_rejected() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-invalid@example.com", name="Generated Onboarding Invalid")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    payload = _generated_onboarding_payload()
    payload["generated_onboarding"]["equipment_pool"] = ["invalid_equipment_tag"]
    response = client.post("/profile/generated-onboarding", headers=headers, json=payload)
    assert response.status_code == 422
    assert "Invalid equipment_pool tag" in response.json()["detail"]


def test_sparse_generated_user_still_generates_with_defaults() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-sparse-generate@example.com", name="Generated Onboarding Sparse")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200


def test_generated_training_profile_prefers_generated_onboarding_payload_when_present() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-mapping@example.com", name="Generated Onboarding Mapping")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    save = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert save.status_code == 200
    plan_router.settings.allow_dev_wipe_endpoints = True
    debug = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert debug.status_code == 200
    payload = debug.json()
    assert payload["path_family"] == "generated"
    assert payload["runtime_active"]["target_days"] == 4
    assert payload["runtime_active"]["session_time_band"] == "low"
    assert payload["runtime_active"]["recovery_modifier"] == "high"
    assert payload["decision_trace"]["generated_onboarding_complete"] is True
    assert payload["decision_trace"]["profile_completeness"] == "high"


def test_generated_onboarding_post_and_get_are_consistent_round_trip() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-roundtrip@example.com", name="Generated Onboarding Roundtrip")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    save = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert save.status_code == 200
    saved = save.json()

    get = client.get("/profile/generated-onboarding", headers=headers)
    assert get.status_code == 200
    fetched = get.json()

    assert fetched["generated_onboarding"] == saved["generated_onboarding"]
    assert fetched["generated_onboarding_complete"] == saved["generated_onboarding_complete"]
    assert fetched["generated_onboarding_version"] == saved["generated_onboarding_version"]
    assert fetched["missing_fields"] == saved["missing_fields"]
    assert fetched["profile_completeness"] == saved["profile_completeness"]


def test_authored_user_remains_authored_even_with_generated_onboarding_saved() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-authored@example.com", name="Generated Onboarding Authored")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        split_preference="full_body",
        days_available=3,
    )
    save = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert save.status_code == 200
    plan_router.settings.allow_dev_wipe_endpoints = True
    debug = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert debug.status_code == 200
    assert debug.json()["path_family"] == "authored"


def test_profile_update_preserves_generated_onboarding_subtree_by_default() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-onboarding-preserve@example.com", name="Generated Onboarding Preserve")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    save = client.post("/profile/generated-onboarding", headers=headers, json=_generated_onboarding_payload())
    assert save.status_code == 200
    assert save.json()["generated_onboarding_complete"] is True

    profile_update = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Generated Onboarding Preserve",
            "age": 31,
            "weight": 83,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "full_body_v1",
            "program_selection_mode": "manual",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell", "machine"],
            "weak_areas": ["chest"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
            "onboarding_answers": {},
        },
    )
    assert profile_update.status_code == 200

    get = client.get("/profile/generated-onboarding", headers=headers)
    assert get.status_code == 200
    payload = get.json()
    assert payload["generated_onboarding_complete"] is True
    assert payload["missing_fields"] == []
