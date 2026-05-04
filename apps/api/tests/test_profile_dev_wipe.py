from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_profile_dev_wipe")

from app.database import Base, engine
from app.main import app
from app.routers import profile as profile_router


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_profile_dev_wipe_removes_current_user_and_data() -> None:
    _reset_db()
    profile_router.settings.allow_dev_wipe_endpoints = True
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "wipe@example.com", "password": "WipePassword1", "name": "Wipe User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Wipe User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 180,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert profile.status_code == 200

    checkin = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": "2026-03-02",
            "body_weight": 82.0,
            "adherence_score": 4,
            "notes": "wipe test",
        },
    )
    assert checkin.status_code == 200

    wipe = client.post("/profile/dev/wipe", headers=headers)
    assert wipe.status_code == 200
    assert wipe.json()["status"] == "wiped"

    after = client.get("/profile", headers=headers)
    assert after.status_code == 401


def test_profile_get_returns_default_payload_before_onboarding() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "profile-defaults@example.com", "password": "ProfileDefaults1", "name": "Defaults User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/profile", headers=headers)
    assert profile.status_code == 200
    payload = profile.json()
    assert payload["selected_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["days_available"] == 2
    assert payload["nutrition_phase"] == "maintenance"
    assert payload["equipment_profile"] == []
    assert payload["weak_areas"] == []
    assert payload["onboarding_answers"] == {}
    assert payload["session_time_budget_minutes"] is None
    assert payload["movement_restrictions"] == []
    assert payload["near_failure_tolerance"] is None


def test_profile_dev_reset_phase1_clears_training_state_and_keeps_account() -> None:
    _reset_db()
    profile_router.settings.allow_dev_wipe_endpoints = True
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase1-reset@example.com", "password": "Phase1Reset1", "name": "Phase 1 Reset"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase 1 Reset",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "days_available": 5,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate_week = client.post("/plan/generate-week", headers=headers, json={})
    assert generate_week.status_code == 200

    apply_adaptation = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert apply_adaptation.status_code == 200

    reset = client.post("/profile/dev/reset-phase1", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["status"] == "reset_to_phase1"

    profile_after = client.get("/profile", headers=headers)
    assert profile_after.status_code == 200
    assert profile_after.json()["selected_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert profile_after.json()["split_preference"] == "full_body"
    assert profile_after.json()["days_available"] == 5

    generated_after_reset = client.post("/plan/generate-week", headers=headers, json={})
    assert generated_after_reset.status_code == 200
    payload_after_reset = generated_after_reset.json()
    assert payload_after_reset["program_template_id"] == "pure_bodybuilding_phase_1_full_body"
    assert len(payload_after_reset["sessions"]) == 5


def test_dev_wipe_disabled_by_default_and_profile_dev_wipe_forbidden() -> None:
    _reset_db()
    profile_router.settings.allow_dev_wipe_endpoints = False
    client = TestClient(app)
    register = client.post(
        "/auth/register",
        json={"email": "wipe-disabled@example.com", "password": "WipeDisabled1", "name": "Wipe Disabled"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    wipe = client.post("/profile/dev/wipe", headers=headers)
    assert wipe.status_code == 403
    assert wipe.json()["detail"] == "Dev wipe endpoints disabled"
