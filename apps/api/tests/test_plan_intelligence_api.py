import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_plan_intelligence_api")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import CoachingRecommendation, WorkoutPlan

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
    recommendation_id = preview_response.json().get("recommendation_id")
    assert isinstance(recommendation_id, str)
    assert recommendation_id
    return recommendation_id


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

    recommendation_id_a = payload_a.pop("recommendation_id")
    recommendation_id_b = payload_b.pop("recommendation_id")
    assert recommendation_id_a
    assert recommendation_id_b
    assert recommendation_id_a != recommendation_id_b
    assert payload_a == payload_b
    assert payload_a["template_id"] == "full_body_v1"
    assert payload_a["schedule"]["from_days"] == 5
    assert payload_a["schedule"]["to_days"] == 3
    assert payload_a["decision_trace"]["interpreter"] == "recommend_coach_intelligence_preview"
    assert payload_a["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_coach_preview_runtime_inputs"
    assert payload_a["decision_trace"]["template_runtime_trace"]["interpreter"] == "recommend_generation_template_selection"
    assert payload_a["decision_trace"]["outputs"]["next_phase"] == payload_a["phase_transition"]["next_phase"]
    assert payload_a["progression"]["action"] in {"progress", "hold", "deload"}
    assert payload_a["progression"]["rationale"]
    assert payload_a["phase_transition"]["next_phase"] in {"accumulation", "intensification", "deload"}
    assert payload_a["phase_transition"]["rationale"]
    assert isinstance(payload_a["specialization"]["focus_muscles"], list)
    assert "video_coverage_pct" in payload_a["media_warmups"]


def test_coach_preview_persists_recommendation_record() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    with SessionLocal() as db:
        recommendation = db.query(CoachingRecommendation).filter(CoachingRecommendation.id == recommendation_id).first()
        assert recommendation is not None
        assert recommendation.recommendation_type == "coach_preview"
        assert recommendation.status == "previewed"
        assert recommendation.recommendation_payload["decision_trace"]["interpreter"] == "recommend_coach_intelligence_preview"


def test_coach_preview_uses_canonical_rules_for_underperformance_without_high_fatigue() -> None:
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
            "completion_pct": 90,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.0,
            "current_phase": "accumulation",
            "weeks_in_phase": 3,
            "stagnation_weeks": 2,
            "lagging_muscles": ["biceps"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    progression_step = next(
        step for step in payload["decision_trace"]["steps"] if step.get("decision") == "progression"
    )
    assert payload["progression"]["action"] == "hold"
    assert payload["progression"]["reason"] == "under_target_without_high_fatigue"
    assert payload["progression"]["rationale"] == (
        "Performance is below target without clear high-fatigue signals. Hold load and accumulate cleaner exposures before changing phase or deloading."
    )
    assert progression_step["result"]["stimulus_fatigue_response"]["deload_pressure"] == "high"
    assert progression_step["result"]["stimulus_fatigue_response"]["fatigue_cost"] == "low"


def test_coach_preview_uses_canonical_readiness_state_when_request_score_omitted() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    today = datetime.now(UTC).date()
    current_monday = today - timedelta(days=today.weekday())

    checkin = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": current_monday.isoformat(),
            "body_weight": 84.0,
            "adherence_score": 4,
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["elbow_flexion"],
            "notes": "Recovery limited",
        },
    )
    assert checkin.status_code == 200

    response = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "full_body_v1",
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 95,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.5,
            "current_phase": "deload",
            "weeks_in_phase": 1,
            "stagnation_weeks": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    readiness_step = next(
        step for step in payload["decision_trace"]["steps"] if step.get("decision") == "readiness_score"
    )
    assert readiness_step["result"]["provided"] is False
    assert readiness_step["result"]["source"] == "context_readiness_state"
    assert payload["phase_transition"]["next_phase"] == "deload"
    assert payload["phase_transition"]["reason"] == "extend_deload_low_readiness"


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
    assert preflight_payload["decision_trace"]["interpreter"] == "interpret_coach_phase_apply_decision"
    assert preflight_payload["decision_trace"]["outcome"]["status"] == "confirmation_required"

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
    assert apply_payload["rationale"]
    assert apply_payload["decision_trace"]["outcome"]["status"] == "applied"
    assert apply_payload["decision_trace"]["outcome"]["applied_recommendation_id"] == apply_payload["applied_recommendation_id"]


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
    assert preflight_payload["decision_trace"]["interpreter"] == "interpret_coach_specialization_apply_decision"

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
    assert apply_payload["decision_trace"]["outcome"]["applied_recommendation_id"] == apply_payload["applied_recommendation_id"]


def test_apply_phase_decision_uses_recommended_phase_fallback_when_preview_payload_omits_it() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    with SessionLocal() as db:
        recommendation = db.query(CoachingRecommendation).filter(CoachingRecommendation.id == recommendation_id).first()
        assert recommendation is not None
        expected_phase = recommendation.recommended_phase
        recommendation.recommendation_payload["phase_transition"] = {
            "reason": "continue_accumulation",
            "rationale": "Stay in accumulation. Current readiness and momentum do not justify a phase change yet.",
        }
        db.add(recommendation)
        db.commit()

    response = client.post(
        "/plan/intelligence/apply-phase",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_phase"] == expected_phase
    assert payload["decision_trace"]["interpreter"] == "interpret_coach_phase_apply_decision"


def test_apply_specialization_decision_rejects_missing_specialization_details() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    with SessionLocal() as db:
        recommendation = db.query(CoachingRecommendation).filter(CoachingRecommendation.id == recommendation_id).first()
        assert recommendation is not None
        recommendation.recommendation_payload = {
            "phase_transition": recommendation.recommendation_payload["phase_transition"],
            "decision_trace": recommendation.recommendation_payload["decision_trace"],
        }
        db.add(recommendation)
        db.commit()

    response = client.post(
        "/plan/intelligence/apply-specialization",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Recommendation is missing specialization details"


def test_recommendation_timeline_returns_preview_and_applied_records_with_rationale() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    recommendation_id = _create_preview_and_recommendation_id(client, headers)

    apply_phase = client.post(
        "/plan/intelligence/apply-phase",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": True},
    )
    assert apply_phase.status_code == 200

    apply_specialization = client.post(
        "/plan/intelligence/apply-specialization",
        headers=headers,
        json={"recommendation_id": recommendation_id, "confirm": True},
    )
    assert apply_specialization.status_code == 200

    timeline = client.get("/plan/intelligence/recommendations?limit=10", headers=headers)
    assert timeline.status_code == 200
    payload = timeline.json()
    entries = payload["entries"]

    assert len(entries) == 3
    types = {entry["recommendation_type"] for entry in entries}
    assert types == {"coach_preview", "phase_decision", "specialization_decision"}

    preview_entry = next(entry for entry in entries if entry["recommendation_type"] == "coach_preview")
    assert preview_entry["recommendation_id"] == recommendation_id
    assert preview_entry["rationale"]
    assert set(preview_entry["focus_muscles"]) == {"biceps", "shoulders"}

    specialization_entry = next(entry for entry in entries if entry["recommendation_type"] == "specialization_decision")
    assert specialization_entry["status"] == "applied"
    assert set(specialization_entry["focus_muscles"]) == {"biceps", "shoulders"}


def test_recommendation_timeline_humanizes_legacy_reason_codes_without_stored_rationale() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    with SessionLocal() as db:
        user_id = db.query(CoachingRecommendation.user_id).first()
        if user_id is None:
            from app.models import User

            user = db.query(User).filter(User.email == "intelligence@example.com").first()
            assert user is not None
            resolved_user_id = user.id
        else:
            resolved_user_id = user_id[0]

        legacy = CoachingRecommendation(
            user_id=resolved_user_id,
            template_id="full_body_v1",
            recommendation_type="coach_preview",
            current_phase="accumulation",
            recommended_phase="accumulation",
            progression_action="hold",
            request_payload={},
            recommendation_payload={
                "progression": {
                    "action": "hold",
                    "load_scale": 1.0,
                    "set_delta": 0,
                    "reason": "under_target_without_high_fatigue",
                },
                "phase_transition": {
                    "next_phase": "accumulation",
                    "reason": "continue_accumulation",
                },
                "specialization": {},
            },
            status="previewed",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(legacy)
        db.commit()

    timeline = client.get("/plan/intelligence/recommendations?limit=10", headers=headers)
    assert timeline.status_code == 200
    payload = timeline.json()
    assert payload["entries"][0]["rationale"] == (
        "Stay in accumulation. Current readiness and momentum do not justify a phase change yet."
    )


def test_coach_preview_surfaces_authored_sequence_completion_for_adaptive_gold() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "intelligence-gold@example.com", "password": TEST_CREDENTIAL, "name": "Gold Coach User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Coach User",
            "age": 31,
            "weight": 84,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2700,
            "protein": 180,
            "fat": 75,
            "carbs": 300,
        },
    )
    assert profile.status_code == 200

    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    with SessionLocal() as db:
        recommendation = db.query(CoachingRecommendation).first()
        assert recommendation is None
        from app.models import User

        user = db.query(User).filter(User.email == "intelligence-gold@example.com").first()
        assert user is not None
        db.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=monday - timedelta(days=7),
                split="full_body",
                phase="intensification",
                payload={
                    "program_template_id": "adaptive_full_body_gold_v0_1",
                    "phase": "intensification",
                    "mesocycle": {
                        "week_index": 10,
                        "trigger_weeks_effective": 10,
                        "authored_week_index": 10,
                        "authored_week_role": "intensification",
                        "authored_sequence_length": 10,
                        "authored_sequence_complete": True,
                        "phase_transition_pending": True,
                        "phase_transition_reason": "authored_sequence_complete",
                        "post_authored_behavior": "hold_last_authored_week",
                    },
                    "sessions": [],
                },
            )
        )
        db.commit()

    response = client.post(
        "/plan/intelligence/coach-preview",
        headers=headers,
        json={
            "template_id": "adaptive_full_body_gold_v0_1",
            "from_days": 3,
            "to_days": 3,
            "completion_pct": 92,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.5,
            "current_phase": "intensification",
            "weeks_in_phase": 4,
            "stagnation_weeks": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase_transition"]["reason"] == "authored_sequence_complete"
    assert payload["phase_transition"]["transition_pending"] is True
    assert payload["phase_transition"]["recommended_action"] == "rotate_program"
    assert payload["phase_transition"]["post_authored_behavior"] == "hold_last_authored_week"
