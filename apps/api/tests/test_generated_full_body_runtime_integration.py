from __future__ import annotations

from copy import deepcopy

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
from app.models import CoachingRecommendation, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan
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


def _missing_session_skeleton_categories(session: dict) -> list[str]:
    patterns = {
        str(exercise.get("movement_pattern") or "")
        for exercise in session.get("exercises") or []
    }
    missing: list[str] = []
    if not {"horizontal_press", "vertical_press"} & patterns:
        missing.append("press")
    if not {"horizontal_pull", "vertical_pull"} & patterns:
        missing.append("pull")
    if not {"squat", "knee_extension", "hinge", "leg_curl"} & patterns:
        missing.append("lower")
    if not {"vertical_press", "lateral_raise", "horizontal_pull"} & patterns:
        missing.append("shoulder_rear_delt")
    return missing


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
    monkeypatch.setattr(runtime_adapter, "prepare_generated_full_body_runtime_template", _unexpected_adapter)

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
        assert trace["constructor_fallback_reason"] == expected_reason


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


# GEN-005 retirement: replaces the former 17 live constructor/adaptive/metadata/
# floor-repair cases. Pure compatibility adapter fixtures above remain in force;
# positive original generation and consent are qualified in test_customized_inventory.
def _legacy_writer_snapshot() -> dict:
    with SessionLocal() as db:
        return {
            'plans': [dict(row) for row in db.execute(WorkoutPlan.__table__.select()).mappings()],
            'profiles': [dict(row) for row in db.execute(User.__table__.select()).mappings()],
            'coaching': [dict(row) for row in db.execute(CoachingRecommendation.__table__.select()).mappings()],
            'customized': {
                table.name: [dict(row) for row in db.execute(table.select()).mappings()]
                for table in Base.metadata.sorted_tables if table.name.startswith('customized_')
            },
        }


@pytest.mark.parametrize('program_id', ['full_body_v1', 'adaptive_full_body_gold_v0_1'])
@pytest.mark.parametrize('selection_mode', ['manual', 'auto'])
@pytest.mark.parametrize('has_history', [False, True], ids=['fresh', 'retained-history'])
def test_retired_generated_writers_require_explicit_original_preview_without_mutation(
    program_id: str, selection_mode: str, has_history: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email='retired-writer@example.com', name='Retirement boundary')
    _post_profile(client, headers=headers, selected_program_id=program_id,
        program_selection_mode=selection_mode, split_preference='full_body',
        training_location='home', equipment_profile=['dumbbell'], days_available=3,
        weak_areas=['arms'], session_time_budget_minutes=45, movement_restrictions=['overhead_pressing'])
    if has_history:
        with SessionLocal() as db:
            user = db.query(User).one()
            db.add(WorkoutPlan(user_id=user.id, week_start=_current_monday() - timedelta(days=7),
                split='full_body', phase='maintenance', payload={'program_template_id': program_id,
                    'sessions': [], 'historical_marker': 'retained-without-replay'}))
            db.commit()

    # A retained recommendation is evidence, never implicit consent to write a plan.
    with SessionLocal() as db:
        user = db.query(User).one()
        db.add(CoachingRecommendation(id='historical-recommendation', user_id=user.id,
            template_id=program_id, recommendation_type='coach_preview', current_phase='accumulation',
            recommended_phase='deload', progression_action='hold', request_payload={},
            recommendation_payload={'historical_fixture': True}, status='previewed'))
        db.commit()

    def unexpected_legacy_constructor(*args, **kwargs):
        raise AssertionError('Retired live writer must not reach the source-based compatibility constructor')
    monkeypatch.setattr(runtime_adapter, 'prepare_generated_full_body_runtime_template', unexpected_legacy_constructor)
    before = _legacy_writer_snapshot()
    # Reuse the unchanged baseline for all seven writers, rather than registering
    # an identical disposable account for each request. Every route must abstain.
    for route, payload in [
        ('/plan/generate-week', {'target_days': 4}),
        ('/plan/next-week', {'target_days': 2}),
        ('/plan/adaptation/preview', {'target_days': 2, 'duration_weeks': 2}),
        ('/plan/adaptation/apply', {'target_days': 2, 'duration_weeks': 2}),
        ('/plan/intelligence/coach-preview', {'from_days': 3, 'to_days': 2}),
        ('/plan/intelligence/apply-phase', {'recommendation_id': 'historical-recommendation', 'confirm': True}),
        ('/plan/intelligence/apply-specialization', {'recommendation_id': 'historical-recommendation', 'confirm': True}),
    ]:
        request = dict(payload)
        if route in ('/plan/adaptation/preview', '/plan/adaptation/apply'): request['program_id'] = program_id
        if route == '/plan/intelligence/coach-preview': request['template_id'] = program_id
        response = client.post(route, headers=headers, json=request)
        assert response.status_code == 409, (route, response.json())
        assert response.json()['detail']['code'] == 'customized_preview_required', route
        assert response.json()['detail']['path'] == '/customize', route
        assert _legacy_writer_snapshot() == before, route
    assert all(not rows for rows in before['customized'].values())
