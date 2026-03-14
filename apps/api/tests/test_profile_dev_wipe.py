from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_profile_dev_wipe")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_profile_dev_wipe_removes_current_user_and_data() -> None:
    _reset_db()
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
