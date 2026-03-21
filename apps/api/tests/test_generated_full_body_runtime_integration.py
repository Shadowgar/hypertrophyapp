from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_generated_full_body_runtime_integration")

from app.database import Base, engine
from app.generated_assessment_schema import ProfileAssessmentInput
from app import generated_full_body_runtime_adapter as runtime_adapter
from app.main import app
from app.program_loader import load_program_template
from app.routers import plan as plan_router
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"
CANONICAL_PROGRAM_ID = runtime_adapter.GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID


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
    training_location: str,
    equipment_profile: list[str],
    days_available: int,
    weak_areas: list[str] | None = None,
    program_selection_mode: str = "manual",
) -> None:
    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Runtime Integration User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": split_preference,
            "selected_program_id": selected_program_id,
            "program_selection_mode": program_selection_mode,
            "training_location": training_location,
            "equipment_profile": equipment_profile,
            "weak_areas": weak_areas or [],
            "days_available": days_available,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200


def test_generate_week_uses_generated_constructor_on_canonical_full_body_compatibility_seam() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-success@example.com",
        name="Generated Runtime Success",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="adaptive_full_body_gold_v0_1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=5,
        weak_areas=["chest", "hamstrings"],
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()

    runtime_trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert payload["program_template_id"] == CANONICAL_PROGRAM_ID
    assert payload["template_selection_trace"]["selected_template_id"] == CANONICAL_PROGRAM_ID
    assert runtime_trace["compatibility_selected_template_id"] == CANONICAL_PROGRAM_ID
    assert runtime_trace["compatibility_program_template_id"] == CANONICAL_PROGRAM_ID
    assert runtime_trace["content_origin"] == "generated_constructor_applied"
    assert runtime_trace["generated_constructor_applied"] is True
    assert runtime_trace["activation_guard_matched"] is True
    assert runtime_trace["anti_copy_guard_mode"] == "doctrine_blueprint_constructor_only"
    assert all(session["session_id"].startswith(f"{CANONICAL_PROGRAM_ID}-") for session in payload["sessions"])
    assert payload["decision_trace"]["outcome"]["content_origin"] == "generated_constructor_applied"
    assert payload["decision_trace"]["outcome"]["generated_constructor_applied"] is True


def test_generate_week_restricted_equipment_falls_back_with_constructor_insufficient() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-fallback@example.com",
        name="Generated Runtime Fallback",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="home",
        equipment_profile=[],
        days_available=3,
        weak_areas=["triceps"],
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()

    runtime_trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert payload["program_template_id"] == CANONICAL_PROGRAM_ID
    assert runtime_trace["content_origin"] == "fallback_to_selected_template"
    assert runtime_trace["generated_constructor_applied"] is False
    assert runtime_trace["fallback_reason"] == runtime_adapter.FALLBACK_REASON_CONSTRUCTOR_INSUFFICIENT
    assert payload["decision_trace"]["outcome"]["content_origin"] == "fallback_to_selected_template"
    assert payload["decision_trace"]["outcome"]["generated_constructor_applied"] is False


def test_non_full_body_runtime_path_does_not_activate_generated_runtime_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_db()
    client = TestClient(app)
    upper_lower_template = {
        "id": "upper_lower_v1",
        "version": "v1",
        "split": "upper_lower",
        "days_supported": [4],
        "deload": {"trigger_weeks": 4, "set_reduction_pct": 40, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
        "sessions": [
            {
                "name": "Upper Day",
                "exercises": [
                    {
                        "id": "db_press",
                        "name": "DB Press",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "start_weight": 20,
                        "equipment_tags": ["dumbbell"],
                    }
                ],
            }
        ],
        "authored_weeks": [],
    }

    def _unexpected_adapter(*args, **kwargs):
        raise AssertionError("Generated full body runtime adapter should not run for non-full-body templates.")

    monkeypatch.setattr(
        plan_router,
        "list_program_templates",
        lambda: [
            {"id": "upper_lower_v1", "split": "upper_lower", "days_supported": [4]},
        ],
    )
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: upper_lower_template)
    monkeypatch.setattr(plan_router, "prepare_generated_full_body_runtime_template", _unexpected_adapter)

    headers = _register_user(
        client,
        email="generated-runtime-upper-lower@example.com",
        name="Generated Runtime Upper Lower",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="upper_lower_v1",
        split_preference="upper_lower",
        training_location="gym",
        equipment_profile=["barbell", "bench", "dumbbell"],
        days_available=4,
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()

    assert payload["program_template_id"] == "upper_lower_v1"
    assert payload["template_selection_trace"]["selected_template_id"] == "upper_lower_v1"
    assert "generated_full_body_runtime_trace" not in payload["template_selection_trace"]


def test_runtime_adapter_stage_failures_return_stable_fallback_reasons(monkeypatch) -> None:
    fixture = get_generated_full_body_archetypes()["novice_gym_full_body"]
    selected_template = load_program_template(CANONICAL_PROGRAM_ID)
    profile_input = ProfileAssessmentInput.model_validate(fixture["profile_input"])
    training_state = fixture["training_state"]

    scenarios = [
        ("load_doctrine_bundle", ValueError("boom"), runtime_adapter.FALLBACK_REASON_BUNDLE_LOAD_FAILED),
        ("build_user_assessment", ValueError("boom"), runtime_adapter.FALLBACK_REASON_ASSESSMENT_VALIDATION_FAILED),
        (
            "build_generated_full_body_blueprint_input",
            ValueError("boom"),
            runtime_adapter.FALLBACK_REASON_BLUEPRINT_VALIDATION_FAILED,
        ),
        (
            "_adapt_draft_to_program_template",
            ValueError("boom"),
            runtime_adapter.FALLBACK_REASON_DRAFT_ADAPTATION_FAILED,
        ),
        (
            "build_generated_full_body_template_draft",
            RuntimeError("boom"),
            runtime_adapter.FALLBACK_REASON_UNEXPECTED_EXCEPTION,
        ),
    ]

    for target_name, exc, expected_reason in scenarios:
        monkeypatch.undo()

        def _raiser(*args, **kwargs):
            raise exc

        monkeypatch.setattr(runtime_adapter, target_name, _raiser)
        result = runtime_adapter.prepare_generated_full_body_runtime_template(
            selected_template_id=CANONICAL_PROGRAM_ID,
            selected_template=selected_template,
            profile_input=profile_input,
            training_state=training_state,
        )
        trace = result["generated_full_body_runtime_trace"]
        assert result["status"] == "fallback_to_selected_template"
        assert trace["generated_constructor_applied"] is False
        assert trace["content_origin"] == "fallback_to_selected_template"
        assert trace["fallback_reason"] == expected_reason


def test_runtime_adapter_not_applicable_for_non_compatibility_template() -> None:
    fixture = get_generated_full_body_archetypes()["novice_gym_full_body"]
    profile_input = ProfileAssessmentInput.model_validate(fixture["profile_input"])
    training_state = fixture["training_state"]
    selected_template = {
        "id": "upper_lower_v1",
        "version": "v1",
        "split": "upper_lower",
        "days_supported": [4],
        "deload": {"trigger_weeks": 4, "set_reduction_pct": 40, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
        "sessions": [],
        "authored_weeks": [],
    }

    result = runtime_adapter.prepare_generated_full_body_runtime_template(
        selected_template_id="upper_lower_v1",
        selected_template=selected_template,
        profile_input=profile_input,
        training_state=training_state,
    )
    trace = result["generated_full_body_runtime_trace"]
    assert result["status"] == "not_applicable"
    assert trace["activation_guard_matched"] is False
    assert trace["generated_constructor_applied"] is False
