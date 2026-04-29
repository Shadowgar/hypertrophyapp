from __future__ import annotations

from datetime import date, timedelta
import uuid

import pytest
from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_generated_full_body_runtime_integration")

from app.database import Base, engine
from app.database import SessionLocal
from app.generated_decision_profile import GeneratedDecisionProfile
from app.generated_training_profile import GeneratedTrainingProfile
from app.generated_assessment_schema import ProfileAssessmentInput
from app import generated_full_body_runtime_adapter as runtime_adapter
from app.knowledge_loader import load_exercise_library
from app.main import app
from app.models import User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan
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


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


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
    session_time_budget_minutes: int | None = None,
    near_failure_tolerance: str | None = None,
    movement_restrictions: list[str] | None = None,
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
            "session_time_budget_minutes": session_time_budget_minutes,
            "near_failure_tolerance": near_failure_tolerance,
            "movement_restrictions": movement_restrictions or [],
        },
    )
    assert response.status_code == 200


def _seed_prior_generated_plan_and_checkin(
    *,
    user_email: str,
    adherence_score: int,
    sleep_quality: int | None,
    stress_level: int | None,
    pain_flags: list[str] | None = None,
    prior_generated_weeks: int = 1,
) -> date:
    current_monday = _current_monday()
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == user_email).first()
        assert user is not None
        for week_offset in range(1, max(1, prior_generated_weeks) + 1):
            session.add(
                WorkoutPlan(
                    user_id=user.id,
                    week_start=current_monday - timedelta(days=7 * week_offset),
                    split="full_body",
                    phase="maintenance",
                    payload={
                        "program_template_id": CANONICAL_PROGRAM_ID,
                        "sessions": [],
                    },
                )
            )
        session.add(
            WeeklyCheckin(
                user_id=user.id,
                week_start=current_monday,
                body_weight=82.0,
                adherence_score=adherence_score,
                sleep_quality=sleep_quality,
                stress_level=stress_level,
                pain_flags=pain_flags or [],
                notes="seeded for generated adaptive loop",
            )
        )
        session.commit()
    return current_monday


def _seed_same_week_review(
    *,
    user_email: str,
    week_start: date,
) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == user_email).first()
        assert user is not None
        session.add(
            WeeklyReviewCycle(
                user_id=user.id,
                reviewed_on=week_start,
                week_start=week_start,
                previous_week_start=week_start - timedelta(days=7),
                body_weight=82.0,
                calories=2500,
                protein=170,
                fat=70,
                carbs=260,
                adherence_score=4,
                notes="manual review wins",
                faults={},
                adjustments={
                    "global": {"set_delta": 1, "weight_scale": 0.95},
                    "exercise_overrides": {},
                    "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
                },
                summary={},
            )
        )
        session.commit()


def _visible_grouped_week_volume(payload: dict) -> dict[str, int]:
    weekly = payload.get("weekly_volume_by_muscle") or {}
    grouped = {
        "chest": int(weekly.get("chest") or 0),
        "back": int(weekly.get("back") or 0),
        "quads": int(weekly.get("quads") or 0),
        "hamstrings": int(weekly.get("hamstrings") or 0),
        "delts": int(weekly.get("shoulders") or 0),
        "arms": int(weekly.get("biceps") or 0) + int(weekly.get("triceps") or 0),
        "core": 0,
    }
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            muscles = [str(item) for item in (exercise.get("primary_muscles") or [])]
            if "abs" in muscles or "core" in muscles:
                grouped["core"] += int(exercise.get("sets") or 0)
    return grouped


def _session_exercise_lookup(payload: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            lookup[str(exercise.get("id") or "")] = exercise
    return lookup


def _has_movement_pattern(payload: dict, patterns: set[str]) -> bool:
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            if str(exercise.get("movement_pattern") or "") in patterns:
                return True
    return False


def _high_fatigue_count(payload: dict) -> int:
    bundle = load_exercise_library()
    fatigue_by_id = {
        str(record.exercise_id): str(record.fatigue_cost or "")
        for record in bundle.records
    }
    return sum(
        1
        for session in payload.get("sessions") or []
        for exercise in session.get("exercises") or []
        if fatigue_by_id.get(str(exercise.get("id") or "")) == "high"
    )


def _assert_metadata_scoring_frozen(runtime_trace: dict) -> None:
    assert runtime_trace["metadata_v2_used_for_scoring"] is False
    assert runtime_trace["metadata_v2_used_for_time_efficiency"] is False
    assert runtime_trace["metadata_v2_used_for_recovery"] is False
    assert runtime_trace["metadata_v2_used_for_role_fit"] is False
    assert runtime_trace["metadata_v2_used_for_overlap"] is False
    assert int(runtime_trace["metadata_v2_scoring_fallback_count"]) == 0


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
    assert "metadata_v2_loaded" in runtime_trace
    assert "metadata_v2_record_count" in runtime_trace
    assert "metadata_v2_candidate_coverage_ratio" in runtime_trace
    assert "metadata_v2_used_for_visible_balance" in runtime_trace
    assert "metadata_v2_fallback_count" in runtime_trace
    assert "metadata_v2_used_for_scoring" in runtime_trace
    assert "metadata_v2_used_for_time_efficiency" in runtime_trace
    assert "metadata_v2_used_for_recovery" in runtime_trace
    assert "metadata_v2_used_for_role_fit" in runtime_trace
    assert "metadata_v2_used_for_overlap" in runtime_trace
    assert "metadata_v2_scoring_fallback_count" in runtime_trace
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


def test_authored_paths_bypass_generated_training_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_db()
    client = TestClient(app)

    def _unexpected_training_profile(*args, **kwargs):
        raise AssertionError("Generated training profile should not run for authored templates.")

    monkeypatch.setattr(plan_router, "build_generated_training_profile", _unexpected_training_profile)

    headers = _register_user(
        client,
        email="authored-bypass-generated-decision@example.com",
        name="Authored Bypass Generated Decision",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "dumbbell"],
        days_available=3,
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["program_template_id"] == "pure_bodybuilding_phase_1_full_body"
    assert "generated_full_body_runtime_trace" not in payload["template_selection_trace"]


def test_generated_training_profile_runtime_active_inputs_take_precedence_for_mode_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_db()
    client = TestClient(app)
    captured: dict[str, int | list[str]] = {}

    def _mock_training_profile(*args, **kwargs):
        decision = GeneratedDecisionProfile.model_validate(
            {
                "selected_program_id": "full_body_v1",
                "path_family": "generated",
                "target_days": 2,
                "session_time_band": "low",
                "recovery_modifier": "standard",
                "training_status": "intermediate",
                "detraining_status": "active",
                "goal_mode": "lean_gain",
                "equipment_scope": "dumbbell",
                "weakpoint_targets": ["arms"],
                "movement_restriction_flags": ["overhead_pressing"],
                "generated_mode": "low_time_full_body",
                "reentry_required": False,
                "decision_trace": {
                    "selected_mode_reason": "session_time_low",
                    "defaults_applied": [],
                    "missing_fields": [],
                    "ignored_future_fields": ["gender", "sex", "height", "weight"],
                    "rule_hits": ["phase1a.mode.low_time"],
                    "insufficient_data_avoided": False,
                },
            }
        )
        return GeneratedTrainingProfile.model_validate(
            {
                "selected_program_id": "full_body_v1",
                "path_family": "generated",
                "decision_profile": decision.model_dump(mode="json"),
                "runtime_active": {
                    "target_days": 2,
                    "session_time_band": "low",
                    "recovery_modifier": "standard",
                    "weakpoint_targets": ["arms"],
                    "movement_restriction_flags": ["overhead_pressing"],
                    "generated_mode": "low_time_full_body",
                },
                "trace_only_controls": {
                    "starting_rir": 3,
                    "high_fatigue_cap": 1,
                    "weekly_volume_band": {"planned_sets_min": 36, "planned_sets_max": 42},
                    "major_muscle_floors": {"chest": 8, "back": 10, "quads": 8, "hamstrings": 8},
                    "arm_delt_caps": {"arm_soft_cap": 10, "delt_soft_cap": 10},
                    "core_floor": 2,
                    "rep_bands": {"main_lift": "6-10", "accessory": "8-15"},
                    "progression_mode": "reps_first",
                    "sex_related_physiology_flag": "off",
                    "anthropometry_flags": {"long_femurs": False, "long_arms": False},
                    "bodyweight_regression_flag": False,
                },
                "decision_trace": {
                    "selected_mode_reason": "session_time_low",
                    "defaults_applied": [],
                    "missing_fields": [],
                    "rule_hits": ["phase1a.mode.low_time", "phase3a.generated_training_profile_bridge_v1"],
                    "trace_only_fields": [
                        "starting_rir",
                        "high_fatigue_cap",
                        "weekly_volume_band",
                        "major_muscle_floors",
                        "arm_delt_caps",
                        "core_floor",
                        "rep_bands",
                        "progression_mode",
                        "sex_related_physiology_flag",
                        "anthropometry_flags",
                        "bodyweight_regression_flag",
                    ],
                    "insufficient_data_avoided": False,
                },
            }
        )

    original_prepare = runtime_adapter.prepare_generated_full_body_runtime_template

    def _capture_prepare(*args, **kwargs):
        profile_input = kwargs["profile_input"]
        assert isinstance(profile_input, ProfileAssessmentInput)
        captured["days_available"] = profile_input.days_available
        captured["weak_areas"] = list(profile_input.weak_areas)
        captured["movement_restrictions"] = list(profile_input.movement_restrictions)
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(plan_router, "build_generated_training_profile", _mock_training_profile)
    monkeypatch.setattr(plan_router, "prepare_generated_full_body_runtime_template", _capture_prepare)

    headers = _register_user(
        client,
        email="generated-decision-precedence@example.com",
        name="Generated Decision Precedence",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "dumbbell", "machine"],
        days_available=5,
        weak_areas=["chest", "hamstrings"],
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    assert captured["days_available"] == 2
    assert captured["weak_areas"] == ["arms"]
    assert captured["movement_restrictions"] == ["overhead_pressing"]


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


def test_generate_week_applies_generated_adaptive_loop_when_no_explicit_review_exists() -> None:
    _reset_db()
    client = TestClient(app)
    email = "generated-adaptive-loop@example.com"
    headers = _register_user(
        client,
        email=email,
        name="Generated Adaptive Loop User",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="adaptive_full_body_gold_v0_1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["hamstrings"],
    )
    _seed_prior_generated_plan_and_checkin(
        user_email=email,
        adherence_score=2,
        sleep_quality=1,
        stress_level=5,
        pain_flags=["shoulder"],
        prior_generated_weeks=3,
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()

    generated_step = next(
        step for step in payload["decision_trace"]["execution_steps"] if step["step"] == "generated_adaptation"
    )
    generated_result = generated_step["result"]
    assert generated_result["interpreter"] == "recommend_generated_full_body_adaptation"
    assert generated_result["outcome"]["status"] in {"applied", "hold"}
    assert "reason" in generated_result["outcome"]
    assert payload["decision_trace"]["outcome"].get("generated_adaptation_applied") in {True, False}
    assert payload["template_selection_trace"]["generated_full_body_runtime_trace"]["generated_constructor_applied"] is True
    block_review_step = next(step for step in payload["decision_trace"]["execution_steps"] if step["step"] == "block_review")
    assert isinstance(block_review_step["result"].get("trend_summary"), dict)
    assert "outcome" in block_review_step["result"]
    assert "reason" in block_review_step["result"]["outcome"]
    assert "interaction_with_weekly_loop" in block_review_step["result"]
    exercise_ids = {
        exercise["primary_exercise_id"]
        for session in payload["sessions"]
        for exercise in session["exercises"]
    }
    adaptive_review = payload.get("adaptive_review")
    if adaptive_review:
        traced_ids = {
            item["exercise_id"] for item in adaptive_review["decision_trace"].get("eligible_targets", [])
        } | {
            item["exercise_id"] for item in adaptive_review["decision_trace"].get("selected_targets", [])
        } | {
            item["exercise_id"] for item in adaptive_review["decision_trace"].get("held_targets", [])
        }
        assert traced_ids <= exercise_ids
    assert exercise_ids == {
        exercise["primary_exercise_id"]
        for session in payload["sessions"]
        for exercise in session["exercises"]
    }


def test_generate_week_explicit_weekly_review_suppresses_generated_adaptive_loop() -> None:
    _reset_db()
    client = TestClient(app)
    email = "generated-adaptive-review-precedence@example.com"
    headers = _register_user(
        client,
        email=email,
        name="Generated Adaptive Review Precedence",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="adaptive_full_body_gold_v0_1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["hamstrings"],
    )
    week_start = _seed_prior_generated_plan_and_checkin(
        user_email=email,
        adherence_score=2,
        sleep_quality=1,
        stress_level=5,
        pain_flags=["shoulder"],
        prior_generated_weeks=3,
    )
    _seed_same_week_review(user_email=email, week_start=week_start)

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()

    assert payload["adaptive_review"]["source"] == "weekly_review"
    assert payload["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    block_review_step = next(step for step in payload["decision_trace"]["execution_steps"] if step["step"] == "block_review")
    assert block_review_step["result"]["outcome"]["reason"] == "explicit_review_precedence"
    generated_step = next(
        step for step in payload["decision_trace"]["execution_steps"] if step["step"] == "generated_adaptation"
    )
    assert generated_step["result"]["outcome"]["reason"] == "explicit_review_precedence"


def test_generate_week_visible_grouped_volume_balancing_is_reflected_in_runtime_payload() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-visible-volume-balance@example.com",
        name="Generated Runtime Visible Balance",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    grouped = _visible_grouped_week_volume(payload)
    planned_sets = sum(
        int(exercise.get("sets") or 0)
        for session in payload.get("sessions") or []
        for exercise in session.get("exercises") or []
    )

    assert planned_sets >= 30
    assert grouped["chest"] >= 7, grouped
    assert grouped["back"] >= 5, grouped
    assert grouped["quads"] >= 4, grouped
    assert grouped["hamstrings"] >= 6, grouped
    assert grouped["arms"] <= 28, grouped
    assert grouped["delts"] <= 18, grouped


def test_generated_runtime_metadata_missing_still_builds_with_trace_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-metadata-missing@example.com",
        name="Generated Runtime Metadata Missing",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
    )
    monkeypatch.setattr(runtime_adapter, "load_exercise_metadata_v2", lambda *args, **kwargs: None)

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    runtime_trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert runtime_trace["content_origin"] == "generated_constructor_applied"
    assert runtime_trace["metadata_v2_loaded"] is False
    assert runtime_trace["metadata_v2_record_count"] == 0
    assert runtime_trace["metadata_v2_candidate_coverage_ratio"] == 0.0
    assert runtime_trace["metadata_v2_used_for_visible_balance"] is False
    assert runtime_trace["metadata_v2_fallback_count"] >= 0
    _assert_metadata_scoring_frozen(runtime_trace)


def test_generated_runtime_metadata_visible_mapping_is_applied_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-metadata-visible-map@example.com",
        name="Generated Runtime Metadata Visible Map",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
    )

    baseline_response = client.post("/plan/generate-week", headers=headers, json={})
    assert baseline_response.status_code == 200
    baseline_payload = baseline_response.json()
    baseline_lookup = _session_exercise_lookup(baseline_payload)
    assert baseline_lookup
    target_id = sorted(baseline_lookup.keys())[0]

    metadata_bundle = runtime_adapter.load_exercise_metadata_v2()
    assert metadata_bundle is not None
    mutated = metadata_bundle.model_copy(deep=True)
    mutated_records = []
    for record in mutated.records:
        if record.exercise_id == target_id:
            rec = record.model_copy(deep=True)
            rec.metadata_v2.muscle_targeting.visible_grouped_muscle_mapping = ["core"]
            mutated_records.append(rec)
        else:
            mutated_records.append(record)
    mutated.records = mutated_records

    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-metadata-visible-map-2@example.com",
        name="Generated Runtime Metadata Visible Map 2",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
    )
    monkeypatch.setattr(runtime_adapter, "load_exercise_metadata_v2", lambda *args, **kwargs: mutated)

    mapped_response = client.post("/plan/generate-week", headers=headers, json={})
    assert mapped_response.status_code == 200
    mapped_payload = mapped_response.json()
    baseline_grouped = _visible_grouped_week_volume(baseline_payload)
    mapped_grouped = _visible_grouped_week_volume(mapped_payload)
    assert baseline_grouped
    assert mapped_grouped

    runtime_trace = mapped_payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert runtime_trace["metadata_v2_loaded"] is True
    assert runtime_trace["metadata_v2_record_count"] >= 1
    assert runtime_trace["metadata_v2_used_for_visible_balance"] is True
    assert runtime_trace["metadata_v2_candidate_coverage_ratio"] > 0.0


def test_generated_runtime_with_metadata_present_is_deterministic_and_reports_coverage() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-metadata-deterministic@example.com",
        name="Generated Runtime Metadata Deterministic",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
    )

    first = client.post("/plan/generate-week", headers=headers, json={})
    second = client.post("/plan/generate-week", headers=headers, json={})
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["sessions"] == second_payload["sessions"]

    runtime_trace = first_payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert runtime_trace["metadata_v2_loaded"] is True
    assert runtime_trace["metadata_v2_record_count"] >= 1
    assert float(runtime_trace["metadata_v2_candidate_coverage_ratio"]) == 1.0
    assert runtime_trace["metadata_v2_fallback_count"] >= 0
    _assert_metadata_scoring_frozen(runtime_trace)


def test_generated_runtime_low_time_metadata_on_preserves_nonzero_viable_exposure() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-low-time-metadata-on@example.com",
        name="Generated Runtime Low Time Metadata",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["quads"],
        session_time_budget_minutes=45,
        near_failure_tolerance="high",
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    grouped = _visible_grouped_week_volume(payload)
    trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert trace["metadata_v2_loaded"] is True
    assert trace["metadata_v2_used_for_visible_balance"] is True
    assert float(trace["metadata_v2_candidate_coverage_ratio"]) == 1.0
    _assert_metadata_scoring_frozen(trace)
    assert grouped["arms"] > 0, grouped
    if _has_movement_pattern(payload, {"vertical_press", "lateral_raise"}):
        assert grouped["delts"] > 0, grouped
    if _has_movement_pattern(payload, {"core"}):
        assert grouped["core"] > 0, grouped
    assert grouped["back"] >= 8, grouped
    assert grouped["quads"] >= 7, grouped
    assert grouped["hamstrings"] >= 4, grouped
    assert grouped["delts"] >= 2, grouped
    assert grouped["arms"] >= 4, grouped
    assert grouped["chest"] >= 2, grouped


def test_generated_runtime_low_recovery_metadata_on_preserves_nonzero_viable_exposure() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-low-recovery-metadata-on@example.com",
        name="Generated Runtime Low Recovery Metadata",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["delts"],
        session_time_budget_minutes=60,
        near_failure_tolerance="low",
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    grouped = _visible_grouped_week_volume(payload)
    trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert trace["metadata_v2_loaded"] is True
    assert trace["metadata_v2_used_for_visible_balance"] is True
    assert float(trace["metadata_v2_candidate_coverage_ratio"]) == 1.0
    _assert_metadata_scoring_frozen(trace)
    assert grouped["arms"] > 0, grouped
    if _has_movement_pattern(payload, {"vertical_press", "lateral_raise"}):
        assert grouped["delts"] > 0, grouped
    if _has_movement_pattern(payload, {"core"}):
        assert grouped["core"] > 0, grouped
    assert grouped["back"] >= 8, grouped
    assert grouped["quads"] >= 7, grouped
    assert grouped["hamstrings"] >= 7, grouped
    assert grouped["delts"] >= 4, grouped
    assert grouped["arms"] >= 4, grouped
    assert grouped["chest"] >= 2, grouped


def test_generated_runtime_metadata_on_does_not_collapse_low_recovery_quads_or_raise_high_fatigue_density(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-low-recovery-metadata-compare@example.com",
        name="Generated Runtime Low Recovery Metadata Compare",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bodyweight", "bench", "cable", "machine", "dumbbell"],
        days_available=3,
        weak_areas=["delts"],
        session_time_budget_minutes=60,
        near_failure_tolerance="low",
    )

    monkeypatch.setattr(runtime_adapter, "load_exercise_metadata_v2", lambda *args, **kwargs: None)
    baseline_response = client.post("/plan/generate-week", headers=headers, json={})
    assert baseline_response.status_code == 200
    baseline_payload = baseline_response.json()
    baseline_grouped = _visible_grouped_week_volume(baseline_payload)
    baseline_high_fatigue = _high_fatigue_count(baseline_payload)

    monkeypatch.undo()
    mapped_response = client.post("/plan/generate-week", headers=headers, json={})
    assert mapped_response.status_code == 200
    mapped_payload = mapped_response.json()
    mapped_grouped = _visible_grouped_week_volume(mapped_payload)
    mapped_high_fatigue = _high_fatigue_count(mapped_payload)
    mapped_trace = mapped_payload["template_selection_trace"]["generated_full_body_runtime_trace"]

    assert mapped_trace["metadata_v2_loaded"] is True
    assert mapped_trace["metadata_v2_used_for_visible_balance"] is True
    _assert_metadata_scoring_frozen(mapped_trace)
    assert mapped_grouped["quads"] >= 6, (baseline_grouped, mapped_grouped)
    assert mapped_high_fatigue <= baseline_high_fatigue, (baseline_high_fatigue, mapped_high_fatigue)


def test_generated_runtime_novice_metadata_on_preserves_core_and_major_group_floors() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-novice-metadata-floors@example.com",
        name="Generated Runtime Novice Metadata Floors",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell", "bodyweight"],
        days_available=3,
        weak_areas=["chest", "hamstrings"],
        session_time_budget_minutes=60,
        near_failure_tolerance="moderate",
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    grouped = _visible_grouped_week_volume(payload)
    trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert trace["metadata_v2_loaded"] is True
    assert trace["metadata_v2_used_for_visible_balance"] is True
    assert float(trace["metadata_v2_candidate_coverage_ratio"]) == 1.0
    _assert_metadata_scoring_frozen(trace)
    assert grouped["chest"] >= 6, grouped
    assert grouped["back"] >= 8, grouped
    assert grouped["quads"] >= 7, grouped
    assert grouped["hamstrings"] >= 6, grouped
    assert grouped["delts"] >= 2, grouped
    assert grouped["arms"] >= 2, grouped
    if _has_movement_pattern(payload, {"core"}):
        assert grouped["core"] >= 2, grouped
    if _has_movement_pattern(payload, {"core"}):
        assert grouped["core"] > 0, grouped


def test_generated_runtime_weakpoint_arms_delts_metadata_on_preserves_core_when_viable() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-runtime-weakpoint-arms-delts-core@example.com",
        name="Generated Runtime Weakpoint Arms Delts Core",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["barbell", "bench", "cable", "machine", "dumbbell", "bodyweight"],
        days_available=3,
        weak_areas=["arms", "delts"],
        session_time_budget_minutes=60,
        near_failure_tolerance="moderate",
    )

    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200
    payload = response.json()
    grouped = _visible_grouped_week_volume(payload)
    trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]

    assert trace["metadata_v2_loaded"] is True
    assert trace["metadata_v2_used_for_visible_balance"] is True
    assert float(trace["metadata_v2_candidate_coverage_ratio"]) == 1.0
    _assert_metadata_scoring_frozen(trace)
    assert grouped["arms"] > 0, grouped
    assert grouped["delts"] > 0, grouped
    assert grouped["chest"] >= 2, grouped
    assert grouped["back"] >= 8, grouped
    assert grouped["quads"] >= 7, grouped
    assert grouped["hamstrings"] >= 7, grouped
    assert grouped["arms"] >= 3, grouped
    assert grouped["delts"] >= 3, grouped
    if _has_movement_pattern(payload, {"core"}):
        assert grouped["core"] >= 2, grouped
