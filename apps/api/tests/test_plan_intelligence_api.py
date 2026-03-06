import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_plan_intelligence_api")

from app.database import Base, engine
from app.main import app

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_onboard(client: TestClient) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": "intelligence@example.com", "password": TEST_CREDENTIAL, "name": "Coach User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Coach User",
            "age": 31,
            "weight": 84,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "full_body_v1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "days_available": 5,
            "nutrition_phase": "maintenance",
            "calories": 2700,
            "protein": 180,
            "fat": 75,
            "carbs": 300,
        },
    )
    assert profile.status_code == 200
    return headers


def test_coach_preview_returns_deterministic_intelligence_payload() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    request_payload = {
        "template_id": "full_body_v1",
        "from_days": 5,
        "to_days": 3,
        "completion_pct": 96,
        "adherence_score": 4,
        "soreness_level": "mild",
        "average_rpe": 8.5,
        "current_phase": "accumulation",
        "weeks_in_phase": 6,
        "stagnation_weeks": 0,
        "lagging_muscles": ["biceps", "shoulders"],
    }

    response_a = client.post("/plan/intelligence/coach-preview", headers=headers, json=request_payload)
    response_b = client.post("/plan/intelligence/coach-preview", headers=headers, json=request_payload)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    payload_a = response_a.json()
    payload_b = response_b.json()

    assert payload_a == payload_b
    assert payload_a["template_id"] == "full_body_v1"
    assert payload_a["schedule"]["from_days"] == 5
    assert payload_a["schedule"]["to_days"] == 3
    assert payload_a["progression"]["action"] in {"progress", "hold", "deload"}
    assert payload_a["phase_transition"]["next_phase"] in {"accumulation", "intensification", "deload"}
    assert isinstance(payload_a["specialization"]["focus_muscles"], list)
    assert "video_coverage_pct" in payload_a["media_warmups"]


def test_reference_pair_endpoint_returns_list_payload() -> None:
    _reset_db()
    client = TestClient(app)

    response = client.get("/plan/intelligence/reference-pairs")
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, list)
    if payload:
        first = payload[0]
        assert "workbook_asset_path" in first
        assert "guide_asset_path" in first
        assert "match_score" in first
