import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_frequency_adaptation_api")

from app.database import Base, engine
from app.main import app

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_profile(client: TestClient) -> dict[str, str]:
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
            "selected_program_id": "full_body_v1",
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


def test_frequency_adaptation_apply_persists_state_for_runtime_generation() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "full_body_v1",
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


def test_frequency_adaptation_apply_completes_after_duration_weeks() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_profile(client)

    apply_response = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": "full_body_v1",
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

    second_week = client.post("/plan/generate-week", headers=headers, json={})
    assert second_week.status_code == 200
    second_payload = second_week.json()
    assert second_payload["user"]["days_available"] == 5
    assert "applied_frequency_adaptation" not in second_payload
