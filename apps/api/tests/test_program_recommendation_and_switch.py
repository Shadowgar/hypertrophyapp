from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_recommendation_and_switch")

from app.database import Base, engine
from app.main import app

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_onboard(client: TestClient) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": "switch@example.com", "password": TEST_CREDENTIAL, "name": "Switch User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Switch User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "ppl",
            "selected_program_id": "ppl_v1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "rack"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    return headers


def test_program_recommendation_endpoint_returns_deterministic_payload() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    payload = recommendation.json()

    assert payload["current_program_id"] == "ppl_v1"
    assert isinstance(payload["compatible_program_ids"], list)
    assert "recommended_program_id" in payload
    assert "reason" in payload


def test_program_switch_requires_confirmation_then_applies() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    target = recommendation.json()["recommended_program_id"]

    if target == "ppl_v1":
        target = "full_body_v1"

    preflight = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": target, "confirm": False},
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()
    assert preflight_payload["status"] in {"confirmation_required", "unchanged"}

    apply = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": target, "confirm": True},
    )
    assert apply.status_code == 200
    apply_payload = apply.json()

    if target == "ppl_v1":
        assert apply_payload["status"] == "unchanged"
    else:
        assert apply_payload["status"] == "switched"
        assert apply_payload["applied"] is True

        profile = client.get("/profile", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["selected_program_id"] == target


def test_program_recommendation_keeps_current_on_low_adherence() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    monday = date.today() - timedelta(days=date.today().weekday())
    checkin = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": monday.isoformat(),
            "body_weight": 82.0,
            "adherence_score": 1,
            "notes": "rough week",
        },
    )
    assert checkin.status_code == 200

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    payload = recommendation.json()

    assert payload["recommended_program_id"] == "ppl_v1"
    assert payload["reason"] == "low_adherence_keep_program"
