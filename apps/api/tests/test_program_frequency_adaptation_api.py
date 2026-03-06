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
