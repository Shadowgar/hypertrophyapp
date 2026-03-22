from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_recommendation_and_switch")

from app.database import Base, engine
from app.main import app
from app.database import SessionLocal
from app.models import User, WorkoutPlan

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
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
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

    assert payload["current_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert isinstance(payload["compatible_program_ids"], list)
    assert "recommended_program_id" in payload
    assert "reason" in payload
    assert payload["rationale"]
    assert payload["decision_trace"]["interpreter"] == "recommend_program_selection"
    assert payload["decision_trace"]["candidate_resolution"]["interpreter"] == "resolve_program_recommendation_candidates"
    assert payload["decision_trace"]["inputs"]["latest_adherence_score_source"] == "training_state"
    assert payload["decision_trace"]["inputs"]["mesocycle_context_source"] == "training_state"


def test_program_recommendation_prefers_high_frequency_adaptation_for_three_days() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    payload = recommendation.json()

    assert payload["current_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["recommended_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["reason"] == "maintain_current_program"
    assert payload["rationale"] == "The current program remains compatible and no stronger rotation signal is present."
    assert payload["decision_trace"]["selected_program_id"] == payload["recommended_program_id"]
    assert payload["recommended_program_id"] in payload["decision_trace"]["candidate_resolution"]["compatible_program_ids"]
    assert payload["decision_trace"]["candidate_resolution"]["compatibility_mode"] == "days_supported_match"


def test_program_switch_requires_confirmation_then_applies() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    target = recommendation.json()["recommended_program_id"]

    preflight = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": target, "confirm": False},
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()
    assert preflight_payload["status"] in {"confirmation_required", "unchanged"}
    assert preflight_payload["rationale"]
    assert preflight_payload["decision_trace"]["switch_outcome"]["status"] in {"confirmation_required", "unchanged"}
    assert preflight_payload["decision_trace"]["candidate_resolution"]["interpreter"] == "resolve_program_recommendation_candidates"

    apply = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": target, "confirm": True},
    )
    assert apply.status_code == 200
    apply_payload = apply.json()

    if target == "pure_bodybuilding_phase_1_full_body":
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

    assert payload["recommended_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["reason"] == "low_adherence_keep_program"
    assert payload["rationale"] == "Recent adherence is low. Keep the current program stable before rotating templates."


def test_program_switch_preflight_matches_recommendation_trace_selection() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    recommendation_payload = recommendation.json()

    preflight = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": recommendation_payload["recommended_program_id"], "confirm": False},
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()

    assert preflight_payload["recommended_program_id"] == recommendation_payload["recommended_program_id"]
    assert preflight_payload["decision_trace"]["selected_program_id"] == recommendation_payload["decision_trace"]["selected_program_id"]
    assert preflight_payload["decision_trace"]["candidate_resolution"]["compatible_program_ids"] == (
        recommendation_payload["decision_trace"]["candidate_resolution"]["compatible_program_ids"]
    )


def test_program_switch_rejects_incompatible_target_program() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    response = client.post(
        "/profile/program-switch",
        headers=headers,
        json={"target_program_id": "bro_split_v1", "confirm": True},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Target program is not compatible"}

    profile = client.get("/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["selected_program_id"] == "pure_bodybuilding_phase_1_full_body"


def test_program_recommendation_rotates_when_adaptive_gold_authored_sequence_is_complete() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "switch-gold@example.com", "password": TEST_CREDENTIAL, "name": "Switch Gold User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Switch Gold User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "switch-gold@example.com").first()
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

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    payload = recommendation.json()

    assert payload["current_program_id"] == "full_body_v1"
    assert payload["recommended_program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["reason"] == "mesocycle_complete_rotate"


def test_plan_generate_week_auto_selection_updates_program_before_template_choice() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "switch-gold-auto@example.com", "password": TEST_CREDENTIAL, "name": "Switch Gold Auto User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Switch Gold Auto User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "program_selection_mode": "auto",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "switch-gold-auto@example.com").first()
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

    recommendation = client.get("/profile/program-recommendation", headers=headers)
    assert recommendation.status_code == 200
    recommendation_payload = recommendation.json()
    recommended_program_id = recommendation_payload["recommended_program_id"]

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["program_template_id"] == recommended_program_id
    assert plan["template_selection_trace"]["program_recommendation_trace"]["outcome"]["recommended_program_id"] == recommended_program_id

    updated_profile = client.get("/profile", headers=headers)
    assert updated_profile.status_code == 200
    assert updated_profile.json()["selected_program_id"] == recommended_program_id
