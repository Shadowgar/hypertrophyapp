import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_plan_intelligence_api")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import CoachingRecommendation, User

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


def _create_preview_and_recommendation_id(client: TestClient, headers: dict[str, str]) -> str:
    preview_payload = {
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

    preview_response = client.post("/plan/intelligence/coach-preview", headers=headers, json=preview_payload)
    assert preview_response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "intelligence@example.com").first()
        assert user is not None
        recommendation = (
            db.query(CoachingRecommendation)
            .filter(
                CoachingRecommendation.user_id == user.id,
                CoachingRecommendation.recommendation_type == "coach_preview",
            )
            .order_by(CoachingRecommendation.created_at.desc())
            .first()
        )
        assert recommendation is not None
        return recommendation.id


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


def test_coach_preview_rejects_invalid_template_id() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    response = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "does_not_exist",
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 90,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "accumulation",
            "weeks_in_phase": 3,
            "stagnation_weeks": 0,
            "lagging_muscles": [],
        },
    )

    assert response.status_code == 404
    assert "Program template not found" in response.json().get("detail", "")


def test_coach_preview_extends_deload_when_readiness_is_low() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    response = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "full_body_v1",
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 88,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "deload",
            "weeks_in_phase": 1,
            "readiness_score": 45,
            "stagnation_weeks": 0,
            "lagging_muscles": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase_transition"]["next_phase"] == "deload"
    assert payload["phase_transition"]["reason"] == "extend_deload_low_readiness"


def test_coach_preview_handles_phase_transition_edge_cases() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    accumulation_complete = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "full_body_v1",
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 98,
            "adherence_score": 5,
            "soreness_level": "none",
            "average_rpe": 8.0,
            "current_phase": "accumulation",
            "weeks_in_phase": 6,
            "readiness_score": 80,
            "stagnation_weeks": 0,
            "lagging_muscles": [],
        },
    )
    assert accumulation_complete.status_code == 200
    accumulation_payload = accumulation_complete.json()
    assert accumulation_payload["phase_transition"]["next_phase"] == "intensification"
    assert accumulation_payload["phase_transition"]["reason"] == "accumulation_complete"

    intensification_cap = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "full_body_v1",
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 92,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.5,
            "current_phase": "intensification",
            "weeks_in_phase": 4,
            "readiness_score": 72,
            "stagnation_weeks": 0,
            "lagging_muscles": [],
        },
    )
    assert intensification_cap.status_code == 200
    intensification_payload = intensification_cap.json()
    assert intensification_payload["phase_transition"]["next_phase"] == "deload"
    assert intensification_payload["phase_transition"]["reason"] == "intensification_fatigue_cap"


def test_coach_preview_persists_recommendation_record() -> None:
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

    response = client.post("/plan/intelligence/coach-preview", headers=headers, json=request_payload)
    assert response.status_code == 200
    body = response.json()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "intelligence@example.com").first()
        assert user is not None

        records = (
            db.query(CoachingRecommendation)
            .filter(CoachingRecommendation.user_id == user.id)
            .order_by(CoachingRecommendation.created_at.desc())
            .all()
        )

        assert len(records) == 1
        record = records[0]
        assert record.recommendation_type == "coach_preview"
        assert record.status == "previewed"
        assert record.template_id == "full_body_v1"
        assert record.current_phase == "accumulation"
        assert record.progression_action == body["progression"]["action"]
        assert record.recommended_phase == body["phase_transition"]["next_phase"]
        assert record.request_payload["from_days"] == 5
        assert record.request_payload["to_days"] == 3
        assert record.recommendation_payload["template_id"] == "full_body_v1"


def test_apply_phase_decision_requires_confirmation_then_applies() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    preflight = client.post(
        "/plan/intelligence/apply-phase",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": False},
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()
    assert preflight_payload["status"] == "confirmation_required"
    assert preflight_payload["requires_confirmation"] is True
    assert preflight_payload["applied"] is False

    apply_response = client.post(
        "/plan/intelligence/apply-phase",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": True},
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["status"] == "applied"
    assert apply_payload["requires_confirmation"] is False
    assert apply_payload["applied"] is True
    assert apply_payload["applied_recommendation_id"]

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "intelligence@example.com").first()
        assert user is not None
        applied_record = (
            db.query(CoachingRecommendation)
            .filter(
                CoachingRecommendation.user_id == user.id,
                CoachingRecommendation.id == apply_payload["applied_recommendation_id"],
            )
            .first()
        )
        assert applied_record is not None
        assert applied_record.recommendation_type == "phase_decision"
        assert applied_record.status == "applied"
        assert applied_record.applied_at is not None


def test_apply_specialization_decision_requires_confirmation_then_applies() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    preflight = client.post(
        "/plan/intelligence/apply-specialization",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": False},
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()
    assert preflight_payload["status"] == "confirmation_required"
    assert preflight_payload["requires_confirmation"] is True
    assert preflight_payload["applied"] is False
    assert isinstance(preflight_payload["focus_muscles"], list)

    apply_response = client.post(
        "/plan/intelligence/apply-specialization",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": True},
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["status"] == "applied"
    assert apply_payload["requires_confirmation"] is False
    assert apply_payload["applied"] is True
    assert apply_payload["applied_recommendation_id"]

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "intelligence@example.com").first()
        assert user is not None
        applied_record = (
            db.query(CoachingRecommendation)
            .filter(
                CoachingRecommendation.user_id == user.id,
                CoachingRecommendation.id == apply_payload["applied_recommendation_id"],
            )
            .first()
        )
        assert applied_record is not None
        assert applied_record.recommendation_type == "specialization_decision"
        assert applied_record.status == "applied"
        assert applied_record.applied_at is not None


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
