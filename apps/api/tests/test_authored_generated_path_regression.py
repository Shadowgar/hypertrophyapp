from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
import uuid
from typing import Any

from fastapi.testclient import TestClient
import pytest

from test_db import configure_test_database

configure_test_database("test_authored_generated_path_regression")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSessionState, WorkoutSetLog
from app.program_loader import load_program_template, resolve_selected_program_binding_id
from app.routers import plan as plan_router
from core_engine.scheduler import AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY


TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register(client: TestClient, *, email: str) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": email, "password": TEST_CREDENTIAL, "name": "Routing Regression User"},
    )
    assert register.status_code == 200
    return {"Authorization": f"Bearer {register.json()['access_token']}"}


def _login(client: TestClient, *, email: str) -> dict[str, str]:
    login = client.post(
        "/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _upsert_profile(
    client: TestClient,
    *,
    headers: dict[str, str],
    selected_program_id: str,
    days_available: int,
    session_time_budget_minutes: int | None = None,
    weak_areas: list[str] | None = None,
) -> dict:
    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Routing Regression User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": selected_program_id,
            "program_selection_mode": "manual",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell", "cable", "machine"],
            "weak_areas": weak_areas or ["chest", "hamstrings"],
            "days_available": days_available,
            "session_time_budget_minutes": session_time_budget_minutes,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200
    return response.json()


def _generate_week(
    client: TestClient,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> dict:
    response = client.post("/plan/generate-week", headers=headers, json=json_body or {})
    assert response.status_code == 200
    return response.json()


def _historical_prescriptions(payload: dict) -> list:
    return [[(e['id'], e['primary_exercise_id'], e['sets'], tuple(e['rep_range']), e['recommended_working_weight'])
        for e in session['exercises']] for session in payload['sessions']]


def _seed_historical_generated_plan(client: TestClient, headers: dict[str, str], *, empty: bool = False) -> dict:
    """Explicit synthetic stored history; never constructs a new Customized program."""
    profile = client.get('/profile', headers=headers)
    assert profile.status_code == 200
    monday = date.today() - timedelta(days=date.today().weekday())
    exercises = [dict(id=id, primary_exercise_id=id, name=name, sets=3, rep_range=[8, 12],
        recommended_working_weight=20.0, start_weight=20.0, movement_pattern=pattern,
        primary_muscles=[muscle], equipment_tags=['machine'], substitution_candidates=[])
        for id, name, pattern, muscle in [('hack_squat', 'Hack squat', 'squat', 'quads'),
            ('chest_supported_machine_row', 'Machine row', 'horizontal_pull', 'back')]]
    payload = {'program_template_id': 'full_body_v1', 'split': 'full_body', 'phase': 'maintenance',
        'week_start': monday.isoformat(), 'historical_fixture': True,
        'mesocycle': {'week_index': 1, 'authored_week_index': 1},
        'weekly_volume_by_muscle': {'quads': 3, 'back': 3},
        'muscle_coverage': {'minimum_sets_per_muscle': 1, 'covered_muscles': ['quads', 'back'],
            'under_target_muscles': [], 'untracked_exercise_count': 0},
        'sessions': [] if empty else [{'session_id': 'full_body_v1-historical-day1',
            'title': 'Historical day 1', 'date': date.today().isoformat(), 'exercises': exercises}]}
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == profile.json()['email']).one()
        db.add(WorkoutPlan(user_id=user.id, week_start=monday, split='full_body',
            phase='maintenance', payload=deepcopy(payload)))
        db.commit()
    return payload


def _log_first_set_for_today(client: TestClient, *, headers: dict[str, str]) -> dict[str, Any]:
    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    exercise = today_payload["exercises"][0]
    weight = (
        exercise.get("recommended_working_weight")
        or exercise.get("recommended_weight")
        or exercise.get("start_weight")
        or 100.0
    )
    log_set = client.post(
        f"/workout/{today_payload['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": exercise["primary_exercise_id"],
            "exercise_id": exercise["id"],
            "set_index": 1,
            "reps": 10,
            "weight": float(weight),
        },
    )
    assert log_set.status_code == 200
    return today_payload


_PRIMARY_COMPOUND_PATTERNS = {
    "horizontal_press",
    "vertical_press",
    "horizontal_pull",
    "vertical_pull",
    "hinge",
    "squat",
}


def _source_week_metrics(program_id: str) -> dict[str, object]:
    template = load_program_template(program_id)
    source_week = template["authored_weeks"][0]
    exercises = [
        exercise
        for session in source_week["sessions"]
        for exercise in session["exercises"]
        if isinstance(exercise, dict)
    ]
    return {
        "exercise_count": len(exercises),
        "set_count": sum(int(exercise.get("sets") or 0) for exercise in exercises),
        "compound_patterns": {
            str(exercise.get("movement_pattern") or "").strip()
            for exercise in exercises
            if str(exercise.get("movement_pattern") or "").strip() in _PRIMARY_COMPOUND_PATTERNS
        },
    }


def _payload_metrics(payload: dict) -> dict[str, object]:
    exercises = [
        exercise
        for session in payload["sessions"]
        for exercise in session["exercises"]
        if isinstance(exercise, dict)
    ]
    return {
        "exercise_count": len(exercises),
        "set_count": sum(int(exercise.get("sets") or 0) for exercise in exercises),
        "compound_patterns": {
            str(exercise.get("movement_pattern") or "").strip()
            for exercise in exercises
            if str(exercise.get("movement_pattern") or "").strip() in _PRIMARY_COMPOUND_PATTERNS
        },
        "session_exercise_counts": [len(session["exercises"]) for session in payload["sessions"]],
    }


def _session_primary_ids(session: dict[str, Any]) -> list[str]:
    return [
        str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
        for exercise in session.get("exercises") or []
        if str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
    ]


def _exercise_id(exercise: dict[str, Any]) -> str:
    return str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()


def _session_set_total(session: dict[str, Any]) -> int:
    return sum(int(exercise.get("sets") or 0) for exercise in session.get("exercises") or [])


def _assert_non_zero_weekly_volume_payload(payload: dict[str, Any]) -> None:
    exercises = [
        exercise
        for session in payload.get("sessions") or []
        for exercise in session.get("exercises") or []
        if isinstance(exercise, dict)
    ]
    planned_sets = sum(int(exercise.get("sets") or 0) for exercise in exercises)
    assert planned_sets > 0

    weekly_volume = payload.get("weekly_volume_by_muscle")
    muscle_coverage = payload.get("muscle_coverage")
    assert isinstance(weekly_volume, dict)
    assert isinstance(muscle_coverage, dict)
    assert weekly_volume

    covered_muscles = {
        str(muscle).strip()
        for muscle in muscle_coverage.get("covered_muscles") or []
        if str(muscle).strip()
    }
    under_target_muscles = {
        str(muscle).strip()
        for muscle in muscle_coverage.get("under_target_muscles") or []
        if str(muscle).strip()
    }
    expected_key_set = covered_muscles | under_target_muscles

    assert expected_key_set
    assert set(weekly_volume.keys()) == expected_key_set
    assert any(int(value) > 0 for value in weekly_volume.values())


def _visible_grouped_week_volume(payload: dict[str, Any]) -> dict[str, int]:
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


def _contains_key(value: Any, target_key: str) -> bool:
    if isinstance(value, dict):
        if target_key in value:
            return True
        return any(_contains_key(item, target_key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, target_key) for item in value)
    return False


def _build_live_like_stale_phase1_payload(payload: dict[str, Any]) -> dict[str, Any]:
    stale = deepcopy(payload)
    stale["mesocycle"]["week_index"] = 2
    stale["mesocycle"]["authored_week_index"] = 2
    first_session_exercises = [
        deepcopy(exercise)
        for exercise in stale["sessions"][0]["exercises"]
        if _exercise_id(exercise)
    ]
    stale["sessions"][0]["exercises"] = first_session_exercises[:5]
    stale["sessions"][0]["exercise_cap_trace"] = {
        "interpreter": "resolve_scheduler_session_exercise_cap",
        "outcome": {
            "exercise_limit": 5,
            "kept_indices": [1, 3, 6, 8, 9],
            "reason_code": "time_budget_cap",
        },
    }
    stale["sessions"][0]["time_budget_trace"] = {
        "budget_minutes": 60,
        "weak_areas": ["biceps", "chest", "triceps"],
        "volume_trimming": {"applied": False, "reduction_steps": 0, "trimmed_exercises": []},
        "exercise_cap": {
            "exercise_limit": 5,
            "kept_indices": [1, 3, 6, 8, 9],
            "selected_threshold": {"maximum_minutes": 60, "exercise_limit": 5},
        },
    }
    return stale


def _assert_authored_program_floor(payload: dict, *, program_id: str) -> None:
    source_metrics = _source_week_metrics(program_id)
    payload_metrics = _payload_metrics(payload)

    assert payload["program_template_id"] == program_id
    assert payload["mesocycle"]["week_index"] == 1
    assert payload["mesocycle"]["authored_week_index"] == 1
    assert len(payload["sessions"]) == 3
    assert "generated_full_body_runtime_trace" not in payload["template_selection_trace"]
    assert payload["template_selection_trace"]["authored_frequency_adaptation_trace"]["status"] == "applied"
    assert all(
        not str(session["title"]).startswith("Generated Full Body")
        for session in payload["sessions"]
    )
    assert any(
        "weak" in str(session["title"]).lower() or "arms" in str(session["title"]).lower()
        for session in payload["sessions"]
    )

    assert int(payload_metrics["exercise_count"]) >= 23
    assert int(payload_metrics["set_count"]) >= int(source_metrics["set_count"]) * 0.70
    assert int(payload_metrics["exercise_count"]) >= int(source_metrics["exercise_count"]) * 0.65
    assert set(source_metrics["compound_patterns"]) <= set(payload_metrics["compound_patterns"])


def _assert_workbook_merged_output(
    payload: dict,
    *,
    program_id: str,
    expected_total_sets: int,
    max_session_spread: int,
) -> None:
    _assert_authored_program_floor(payload, program_id=program_id)
    assert [session["title"] for session in payload["sessions"]] == [
        "Full Body #1 + Full Body #2",
        "Full Body #3 + Full Body #4",
        "Arms & Weak Points",
    ]
    session_totals = [_session_set_total(session) for session in payload["sessions"]]
    assert sum(session_totals) == expected_total_sets
    assert max(session_totals) - min(session_totals) <= max_session_spread


def test_program_catalog_exposes_three_distinct_selectable_paths() -> None:
    _reset_db()
    client = TestClient(app)

    response = client.get("/plan/programs")
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
        "full_body_v1",
    ]


def test_fresh_onboarding_authored_phase1_starts_week1_and_stays_authored_derived() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-routing@example.com")

    profile = _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )
    assert profile["selected_program_id"] == "pure_bodybuilding_phase_1_full_body"

    payload = _generate_week(client, headers=headers)
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_1_full_body",
        expected_total_sets=88,
        max_session_spread=2,
    )
    assert payload["mesocycle"]["authored_week_role"] == "adaptation"
    assert payload["mesocycle"]["is_deload_week"] is False


def test_fresh_onboarding_authored_phase1_five_day_plan_is_exact_workbook_week_one() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-exact-five-day@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=5,
    )

    payload = _generate_week(client, headers=headers)

    assert payload["program_template_id"] == "pure_bodybuilding_phase_1_full_body"
    assert "generated_full_body_runtime_trace" not in payload["template_selection_trace"]
    assert payload["mesocycle"]["authored_week_index"] == 1
    assert payload["mesocycle"]["authored_week_role"] == "adaptation"
    assert [session["title"] for session in payload["sessions"]] == [
        "Full Body #1",
        "Full Body #2",
        "Full Body #3",
        "Full Body #4",
        "Arms & Weak Points",
    ]
    assert [_session_set_total(session) for session in payload["sessions"]] == [18, 16, 20, 16, 18]
    assert [
        [exercise["name"] for exercise in session["exercises"]]
        for session in payload["sessions"]
    ] == [
        [
            "Cross-Body Lat Pull-Around",
            "Low Incline Smith Machine Press",
            "Machine Hip Adduction",
            "Leg Press",
            "Lying Paused Rope Face Pull",
            "Cable Crunch",
        ],
        [
            "Seated DB Shoulder Press",
            "Paused Barbell RDL",
            "Chest-Supported Machine Row",
            "Hammer Preacher Curl",
            "Cuffed Behind-The-Back Lateral Raise",
            "Overhead Cable Triceps Extension (Bar)",
        ],
        [
            "Superset A1: Assisted Pull-Up",
            "Superset A2: Paused Assisted Dip",
            "Superset B1: Seated Leg Curl",
            "Superset B2: Leg Extension",
            "Cable Paused Shrug-In",
            "Roman Chair Leg Raise",
        ],
        [
            "Lying Leg Curl",
            "Hack Squat",
            "Bent-Over Cable Pec Flye",
            "Neutral-Grip Lat Pulldown",
            "Leg Press Calf Press",
            "Cable Reverse Flye (Mechanical Dropset)",
        ],
        [
            "Weak Point Exercise 1",
            "Weak Point Exercise 2 (optional)",
            "Bayesian Cable Curl",
            "Triceps Pressdown (Bar)",
            "Bottom-2/3 Constant Tension Preacher Curl",
            "Cable Triceps Kickback",
            "Standing Calf Raise",
        ],
    ]


def test_authored_phase1_session_time_budget_does_not_disable_workbook_passthrough() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-budget-routing@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
        session_time_budget_minutes=60,
    )

    payload = _generate_week(client, headers=headers)
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_1_full_body",
        expected_total_sets=88,
        max_session_spread=2,
    )


def test_authored_phase1_regenerate_with_target_days_three_preserves_workbook_passthrough() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-target-days-regenerate@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=5,
    )

    payload = _generate_week(client, headers=headers, json_body={"target_days": 3})
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_1_full_body",
        expected_total_sets=88,
        max_session_spread=2,
    )


def test_fresh_onboarding_authored_phase2_starts_week1_and_stays_authored_derived() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase2-routing@example.com")

    profile = _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_2_full_body",
        days_available=3,
    )
    assert profile["selected_program_id"] == "pure_bodybuilding_phase_2_full_body"

    payload = _generate_week(client, headers=headers)
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_2_full_body",
        expected_total_sets=67,
        max_session_spread=2,
    )
    assert payload["mesocycle"]["authored_week_role"] == "intensification"
    assert payload["mesocycle"]["is_deload_week"] is False


def test_authored_phase2_regenerate_with_target_days_three_preserves_workbook_passthrough() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase2-target-days-regenerate@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_2_full_body",
        days_available=5,
    )

    payload = _generate_week(client, headers=headers, json_body={"target_days": 3})
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_2_full_body",
        expected_total_sets=67,
        max_session_spread=2,
    )


def test_generated_program_selection_requires_original_preview_and_explicit_consent() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="generated-routing@example.com")

    profile = _upsert_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        days_available=3,
    )
    assert profile["selected_program_id"] == "full_body_v1"

    response = client.post('/plan/generate-week', headers=headers, json={})
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'customized_preview_required'
    assert response.json()['detail']['path'] == '/customize'
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).count() == 0
    assert client.get('/profile', headers=headers).json()['selected_program_id'] == 'full_body_v1'


def test_authored_phase_histories_are_isolated_from_each_other_and_generated_history() -> None:
    _reset_db()
    client = TestClient(app)
    email = "history-isolation@example.com"
    headers = _register(client, email=email)

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        days_available=3,
    )
    generated_payload = _seed_historical_generated_plan(client, headers)
    assert generated_payload["program_template_id"] == "full_body_v1"
    headers = _login(client, email=email)

    phase1_profile = _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )
    assert phase1_profile["selected_program_id"] == "pure_bodybuilding_phase_1_full_body"
    phase1_payload = _generate_week(client, headers=headers)
    assert phase1_payload["program_template_id"] == "pure_bodybuilding_phase_1_full_body"
    assert phase1_payload["mesocycle"]["week_index"] == 1
    assert phase1_payload["mesocycle"]["authored_week_index"] == 1
    headers = _login(client, email=email)

    phase2_profile = _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_2_full_body",
        days_available=3,
    )
    assert phase2_profile["selected_program_id"] == "pure_bodybuilding_phase_2_full_body"
    phase2_payload = _generate_week(client, headers=headers)
    assert phase2_payload["program_template_id"] == "pure_bodybuilding_phase_2_full_body"
    assert phase2_payload["mesocycle"]["week_index"] == 1
    assert phase2_payload["mesocycle"]["authored_week_index"] == 1


def test_workbook_merged_sessions_enter_scheduler_and_exit_unchanged_for_authored_phase1() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-scheduler-passthrough@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
        session_time_budget_minutes=60,
    )

    original_generate_week_plan = plan_router.generate_week_plan
    captured_scheduler_sessions: list[dict[str, Any]] = []

    def _capturing_generate_week_plan(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured_scheduler_sessions[:] = [
            {
                "name": str(session.get("name") or ""),
                "exercise_ids": _session_primary_ids(session),
                "set_total": _session_set_total(session),
            }
            for session in (kwargs["program_template"].get("sessions") or [])
        ]
        return original_generate_week_plan(*args, **kwargs)

    plan_router.generate_week_plan = _capturing_generate_week_plan
    try:
        payload = _generate_week(client, headers=headers)
    finally:
        plan_router.generate_week_plan = original_generate_week_plan

    assert [item["name"] for item in captured_scheduler_sessions] == [
        "Full Body #1 + Full Body #2",
        "Full Body #3 + Full Body #4",
        "Arms & Weak Points",
    ]
    captured_totals = [int(item["set_total"]) for item in captured_scheduler_sessions]
    assert sum(captured_totals) == 88
    assert max(captured_totals) - min(captured_totals) <= 2
    assert [
        {
            "name": session["title"],
            "exercise_ids": _session_primary_ids(session),
            "set_total": _session_set_total(session),
        }
        for session in payload["sessions"]
    ] == captured_scheduler_sessions


def test_passthrough_marker_is_scoped_to_workbook_derived_authored_5_to_3_path_only() -> None:
    _reset_db()
    client = TestClient(app)
    email = "passthrough-scope@example.com"
    headers = _register(client, email=email)

    original_generate_week_plan = plan_router.generate_week_plan
    captured_flags: list[bool] = []

    def _capturing_generate_week_plan(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured_flags.append(bool(kwargs["program_template"].get(AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY)))
        return original_generate_week_plan(*args, **kwargs)

    plan_router.generate_week_plan = _capturing_generate_week_plan
    try:
        _upsert_profile(
            client,
            headers=headers,
            selected_program_id="pure_bodybuilding_phase_1_full_body",
            days_available=3,
        )
        authored_payload = _generate_week(client, headers=headers)
        headers = _login(client, email=email)

        _upsert_profile(
            client,
            headers=headers,
            selected_program_id="full_body_v1",
            days_available=3,
        )
        rejected = client.post('/plan/generate-week', headers=headers, json={})
    finally:
        plan_router.generate_week_plan = original_generate_week_plan

    assert captured_flags == [True]
    assert "generated_full_body_runtime_trace" not in authored_payload["template_selection_trace"]
    assert rejected.status_code == 409
    assert rejected.json()['detail']['code'] == 'customized_preview_required'
    assert rejected.json()['detail']['path'] == '/customize'


def test_authoritative_passthrough_marker_never_appears_in_api_or_persisted_payloads() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="passthrough-hidden@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )

    generated_payload = _generate_week(client, headers=headers)
    latest_payload = client.get("/plan/latest-week", headers=headers)
    assert latest_payload.status_code == 200

    with SessionLocal() as db:
        record = db.query(WorkoutPlan).order_by(WorkoutPlan.created_at.desc()).first()
        assert record is not None
        persisted_payload = record.payload

    assert _contains_key(generated_payload, AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY) is False
    assert _contains_key(latest_payload.json(), AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY) is False
    assert _contains_key(persisted_payload, AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY) is False


def test_same_binding_onboarding_refresh_without_progress_resets_authored_week_to_one() -> None:
    _reset_db()
    client = TestClient(app)
    email = "same-binding-reset@example.com"
    headers = _register(client, email=email)

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_2_full_body",
        days_available=3,
    )
    _generate_week(client, headers=headers)
    headers = _login(client, email=email)

    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Routing Regression User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "program_selection_mode": "manual",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell", "cable", "machine"],
            "weak_areas": ["chest", "hamstrings"],
            "onboarding_answers": {"restart": True},
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200

    payload = _generate_week(client, headers=headers)
    assert payload["mesocycle"]["week_index"] == 1
    assert payload["mesocycle"]["authored_week_index"] == 1


@pytest.mark.parametrize(
    ("days_available", "expected_total_sets", "max_session_spread"),
    [
        # A whole-slot, source-ordered cut cannot land at 44: the authored
        # B1/B2 pair spans the nearest boundary, leaving a 42/46 split.
        (2, 88, 4),
        (3, 88, 2),
        (4, 88, 4),
        (5, 88, 4),
    ],
)
def test_phase1_week1_authored_dose_preserving_redistribution_by_day_count(
    days_available: int,
    expected_total_sets: int,
    max_session_spread: int,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"phase1-dose-redistribution-{days_available}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=days_available,
        weak_areas=["chest", "hamstrings"],
    )
    payload = _generate_week(client, headers=headers)
    assert payload["mesocycle"]["authored_week_index"] == 1
    session_totals = [_session_set_total(session) for session in payload["sessions"]]
    assert len(session_totals) == days_available
    assert sum(session_totals) == expected_total_sets
    assert max(session_totals) - min(session_totals) <= max_session_spread
    if days_available == 2:
        assert sorted(session_totals) == [42, 46]
    trace = payload["template_selection_trace"]["authored_frequency_adaptation_trace"]
    if days_available < 5:
        assert trace["authored_adaptation_policy"] == "dose_preserving_redistribution"
        assert int(trace["authored_redistribution_preserved_weekly_sets"]) == expected_total_sets


def test_phase1_week5_semi_deload_preserves_source_dose_in_five_day_mode() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="phase1-week5-five-day-dose@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=5,
        weak_areas=["chest", "hamstrings"],
    )

    # Advance authored-family week index to week 5 by generating the next week sequentially.
    payload = _generate_week(client, headers=headers)
    for _ in range(4):
        next_week = client.post("/plan/next-week", headers=headers, json={})
        assert next_week.status_code == 200
        payload = next_week.json()

    assert payload["mesocycle"]["authored_week_index"] == 5
    session_totals = [_session_set_total(session) for session in payload["sessions"]]
    assert len(session_totals) == 5
    assert sum(session_totals) == 75


def test_latest_week_today_and_progress_auto_regenerate_stale_authored_phase1_rows() -> None:
    _reset_db()
    client = TestClient(app)
    email = "stale-authored-latest@example.com"
    headers = _register(client, email=email)

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )
    current_payload = _generate_week(client, headers=headers)
    stale_payload = _build_live_like_stale_phase1_payload(current_payload)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        db.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=date.fromisoformat(current_payload["week_start"]),
                split=current_payload["split"],
                phase=current_payload["phase"],
                payload=stale_payload,
            )
        )
        db.commit()

    latest_week = client.get("/plan/latest-week", headers=headers)
    assert latest_week.status_code == 200
    latest_payload = latest_week.json()
    _assert_workbook_merged_output(
        latest_payload,
        program_id="pure_bodybuilding_phase_1_full_body",
        expected_total_sets=88,
        max_session_spread=2,
    )

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    assert today_payload["mesocycle"]["week_index"] == 1
    assert today_payload["mesocycle"]["authored_week_index"] == 1
    expected_today_sets = _session_set_total(latest_payload["sessions"][0])
    assert _session_set_total(today_payload) == expected_today_sets
    assert int(today_payload.get("total_sets") or 0) == expected_today_sets

    progress = client.get(f"/workout/{today_payload['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    progress_payload = progress.json()
    assert progress_payload["planned_total"] == expected_today_sets
    assert sum(int(item["planned_sets"]) for item in progress_payload["exercises"]) == expected_today_sets

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        phase1_rows = [
            row
            for row in db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).all()
            if resolve_selected_program_binding_id((row.payload or {}).get("program_template_id"))
            == "pure_bodybuilding_phase_1_full_body"
        ]
        assert len(phase1_rows) == 1
        persisted_payload = phase1_rows[0].payload
        assert _session_set_total(persisted_payload["sessions"][0]) == expected_today_sets


@pytest.mark.parametrize(
    ("selected_program_id", "expected_total_sets"),
    [
        ("pure_bodybuilding_phase_1_full_body", 30),
        ("pure_bodybuilding_phase_2_full_body", 23),
    ],
)
def test_today_total_sets_matches_progress_planned_total(
    selected_program_id: str,
    expected_total_sets: int,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"today-total-sets-{selected_program_id}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )
    _generate_week(client, headers=headers)

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()

    progress = client.get(f"/workout/{today_payload['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    progress_payload = progress.json()

    assert int(today_payload.get("total_sets") or 0) == expected_total_sets
    assert int(progress_payload.get("planned_total") or 0) == expected_total_sets
    assert int(today_payload.get("total_sets") or 0) == int(progress_payload.get("planned_total") or 0)


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_generate_and_latest_week_volume_by_muscle_non_zero_when_planned_sets_exist(
    selected_program_id: str,
) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"volume-by-muscle-{selected_program_id}@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )

    generated_payload = _generate_week(client, headers=headers)
    latest_week = client.get("/plan/latest-week", headers=headers)
    assert latest_week.status_code == 200
    latest_payload = latest_week.json()

    _assert_non_zero_weekly_volume_payload(generated_payload)
    _assert_non_zero_weekly_volume_payload(latest_payload)


def test_historical_generated_latest_read_preserves_stored_volume_and_slots() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email='historical-volume@example.com')
    _upsert_profile(client, headers=headers, selected_program_id='full_body_v1', days_available=3)
    stored = _seed_historical_generated_plan(client, headers)
    latest = client.get('/plan/latest-week', headers=headers)
    assert latest.status_code == 200
    assert latest.json()['weekly_volume_by_muscle'] == stored['weekly_volume_by_muscle']
    assert _visible_grouped_week_volume(latest.json()) == _visible_grouped_week_volume(stored)
    assert _historical_prescriptions(latest.json()) == _historical_prescriptions(stored)


def test_profile_weakpoint_changes_do_not_rewrite_historical_generated_plan() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email='historical-weakpoints@example.com')
    _upsert_profile(client, headers=headers, selected_program_id='full_body_v1', days_available=3, weak_areas=['chest'])
    stored = _seed_historical_generated_plan(client, headers)
    _upsert_profile(client, headers=headers, selected_program_id='full_body_v1', days_available=3, weak_areas=['biceps', 'side_delts'])
    latest = client.get('/plan/latest-week', headers=headers)
    assert latest.status_code == 200
    assert _visible_grouped_week_volume(latest.json()) == _visible_grouped_week_volume(stored)
    assert _historical_prescriptions(latest.json()) == _historical_prescriptions(stored)


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_current_week_regenerate_keeps_displayed_and_authored_week_indices(selected_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"regenerate-current-week-{selected_program_id}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )

    first = _generate_week(client, headers=headers)
    regenerated = _generate_week(client, headers=headers)
    latest = client.get("/plan/latest-week", headers=headers)
    assert latest.status_code == 200
    latest_payload = latest.json()

    assert regenerated["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert regenerated["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]
    assert latest_payload["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert latest_payload["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_current_week_regenerate_with_progress_is_blocked(selected_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"regenerate-with-activity-{selected_program_id}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )

    first = _generate_week(client, headers=headers)
    _log_first_set_for_today(client, headers=headers)

    latest = client.get("/plan/latest-week", headers=headers)
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert latest_payload["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_blocked_regenerate_preserves_progress_artifacts_and_plan_payload(selected_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    email = f"regenerate-preserve-progress-{selected_program_id}@example.com"
    headers = _register(client, email=email)
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )

    _generate_week(client, headers=headers)
    today_payload = _log_first_set_for_today(client, headers=headers)
    selected_session_id = today_payload["session_id"]
    monday = date.today() - timedelta(days=date.today().weekday())

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        before_logs = (
            db.query(WorkoutSetLog)
            .filter(WorkoutSetLog.user_id == user.id, WorkoutSetLog.workout_id == selected_session_id)
            .count()
        )
        before_states = (
            db.query(WorkoutSessionState)
            .filter(WorkoutSessionState.user_id == user.id, WorkoutSessionState.workout_id == selected_session_id)
            .count()
        )
        row = (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user.id, WorkoutPlan.week_start == monday)
            .order_by(WorkoutPlan.created_at.desc())
            .first()
        )
        assert row is not None
        before_plan_payload = deepcopy(row.payload if isinstance(row.payload, dict) else {})

    blocked = client.post("/plan/generate-week", headers=headers, json={})
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "This week has logged workout data. Regenerating would replace the current plan and clear progress."

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        after_logs = (
            db.query(WorkoutSetLog)
            .filter(WorkoutSetLog.user_id == user.id, WorkoutSetLog.workout_id == selected_session_id)
            .count()
        )
        after_states = (
            db.query(WorkoutSessionState)
            .filter(WorkoutSessionState.user_id == user.id, WorkoutSessionState.workout_id == selected_session_id)
            .count()
        )
        row = (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user.id, WorkoutPlan.week_start == monday)
            .order_by(WorkoutPlan.created_at.desc())
            .first()
        )
        assert row is not None
        after_plan_payload = deepcopy(row.payload if isinstance(row.payload, dict) else {})

    assert after_logs == before_logs
    assert after_states == before_states
    assert after_plan_payload == before_plan_payload


def test_program_selection_update_is_non_destructive_even_with_logged_progress_and_regenerate_stays_blocked() -> None:
    _reset_db()
    client = TestClient(app)
    email = "non-destructive-program-selection-update@example.com"
    headers = _register(client, email=email)
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )

    _generate_week(client, headers=headers)
    _log_first_set_for_today(client, headers=headers)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        before_logs = db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user.id).count()
        before_states = db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user.id).count()
        before_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count()

    update = client.post(
        "/profile/program-selection",
        headers=headers,
        json={"selected_program_id": "full_body_v1", "program_selection_mode": "manual"},
    )
    assert update.status_code == 200
    assert update.json()["selected_program_id"] == "full_body_v1"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        after_logs = db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user.id).count()
        after_states = db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user.id).count()
        after_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count()

    assert after_logs == before_logs
    assert after_states == before_states
    assert after_plans == before_plans


    rejected = client.post('/plan/generate-week', headers=headers, json={})
    assert rejected.status_code == 409
    assert rejected.json()['detail']['code'] == 'customized_preview_required'
    assert rejected.json()['detail']['path'] == '/customize'
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).count() == before_logs
        assert db.query(WorkoutSessionState).count() == before_states
        assert db.query(WorkoutPlan).count() == before_plans

def test_current_week_regenerate_does_not_block_for_progress_on_different_binding() -> None:
    _reset_db()
    client = TestClient(app)
    email = "regenerate-other-binding-progress@example.com"
    headers = _register(client, email=email)
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )

    _generate_week(client, headers=headers)
    switched_generation = _seed_historical_generated_plan(client, headers)
    assert switched_generation["program_template_id"] == "full_body_v1"
    switched_session = switched_generation["sessions"][0]
    switched_exercise = switched_session["exercises"][0]
    logged = client.post(
        f"/workout/{switched_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": switched_exercise.get("primary_exercise_id"),
            "exercise_id": switched_exercise["id"],
            "set_index": 1,
            "reps": 10,
            "weight": float(switched_exercise.get("recommended_working_weight") or 20.0),
        },
    )
    assert logged.status_code == 200

    switch_back = client.post(
        "/plan/generate-week",
        headers=headers,
        json={"template_id": "pure_bodybuilding_phase_1_full_body"},
    )
    assert switch_back.status_code == 200
    assert switch_back.json()["program_template_id"] == "pure_bodybuilding_phase_1_full_body"


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_current_week_regenerate_ignores_stale_prior_rows_for_week_progression(selected_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    email = f"regenerate-stale-prior-{selected_program_id}@example.com"
    headers = _register(client, email=email)
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )
    first = _generate_week(client, headers=headers)
    monday = date.today() - timedelta(days=date.today().weekday())
    stale_week_start = monday - timedelta(days=28)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        row = (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user.id)
            .order_by(WorkoutPlan.created_at.desc())
            .first()
        )
        assert row is not None
        payload = deepcopy(row.payload if isinstance(row.payload, dict) else {})
        payload["week_start"] = stale_week_start.isoformat()
        row.week_start = stale_week_start
        row.payload = payload
        db.add(row)
        db.commit()

    regenerated = _generate_week(client, headers=headers)
    latest = client.get("/plan/latest-week", headers=headers)
    assert latest.status_code == 200
    latest_payload = latest.json()

    assert regenerated["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert regenerated["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]
    assert latest_payload["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert latest_payload["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]


@pytest.mark.parametrize(
    "selected_program_id",
    [
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
    ],
)
def test_next_week_advance_increments_week_index(selected_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"advance-next-week-{selected_program_id}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id=selected_program_id,
        days_available=3,
    )

    current_week = _generate_week(client, headers=headers)
    next_week_response = client.post("/plan/next-week", headers=headers, json={})
    assert next_week_response.status_code == 200
    next_week_payload = next_week_response.json()

    assert int(next_week_payload["mesocycle"]["week_index"]) == int(current_week["mesocycle"]["week_index"]) + 1


@pytest.mark.parametrize(
    "switch_template_id",
    ["pure_bodybuilding_phase_2_full_body"],
)
def test_template_override_switch_persists_selected_program_consistently(switch_template_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email=f"switch-consistency-{switch_template_id}@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )
    _generate_week(client, headers=headers)

    switched_generation = _generate_week(client, headers=headers, json_body={"template_id": switch_template_id})
    assert switched_generation["program_template_id"] == switch_template_id

    profile = client.get("/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["selected_program_id"] == switch_template_id

    latest_week = client.get("/plan/latest-week", headers=headers)
    assert latest_week.status_code == 200
    assert latest_week.json()["program_template_id"] == switch_template_id

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    assert today.json()["program_template_id"] == switch_template_id


def test_same_binding_onboarding_refresh_ignores_checkins_and_reviews_without_workout_activity() -> None:
    _reset_db()
    client = TestClient(app)
    email = "same-binding-admin-only@example.com"
    headers = _register(client, email=email)

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_2_full_body",
        days_available=3,
    )
    _generate_week(client, headers=headers)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        week_start = date.today() - timedelta(days=date.today().weekday())
        db.add(
            WeeklyCheckin(
                user_id=user.id,
                week_start=week_start,
                body_weight=82.0,
                adherence_score=4,
                sleep_quality=3,
                stress_level=2,
                pain_flags=[],
                notes="admin-only checkin",
            )
        )
        db.add(
            WeeklyReviewCycle(
                user_id=user.id,
                reviewed_on=date.today(),
                week_start=week_start,
                previous_week_start=week_start - timedelta(days=7),
                body_weight=82.0,
                calories=2600,
                protein=180,
                fat=70,
                carbs=280,
                adherence_score=4,
                notes="admin-only review",
                faults={},
                adjustments={},
                summary={},
            )
        )
        db.commit()

    headers = _login(client, email=email)
    response = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Routing Regression User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "program_selection_mode": "manual",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell", "cable", "machine"],
            "weak_areas": ["chest", "hamstrings"],
            "onboarding_answers": {"restart": True},
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200

    payload = _generate_week(client, headers=headers)
    _assert_workbook_merged_output(
        payload,
        program_id="pure_bodybuilding_phase_2_full_body",
        expected_total_sets=67,
        max_session_spread=2,
    )


@pytest.mark.parametrize('scenario', ['unstarted', 'logged-progress', 'empty-sessions', 'stale-exercise-state'])
def test_retired_generated_regeneration_preserves_existing_history_and_profile(scenario: str) -> None:
    """Generated branches formerly shared by the Authored regeneration matrix."""
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email='retained-generated-history@example.com')
    _upsert_profile(client, headers=headers, selected_program_id='full_body_v1', days_available=3)
    _seed_historical_generated_plan(client, headers, empty=scenario == 'empty-sessions')
    if scenario == 'logged-progress':
        _log_first_set_for_today(client, headers=headers)
    if scenario == 'stale-exercise-state':
        with SessionLocal() as db:
            user = db.query(User).one()
            db.add(ExerciseState(user_id=user.id, exercise_id='hack_squat', current_working_weight=20.0,
                exposure_count=2, consecutive_under_target_exposures=0, last_progression_action='hold',
                fatigue_score=0.0, last_updated_at=datetime.now().replace(tzinfo=None) - timedelta(days=10)))
            db.commit()

    def snapshot() -> dict:
        with SessionLocal() as db:
            return {model.__tablename__: [dict(row) for row in db.execute(model.__table__.select()).mappings()]
                for model in (User, WorkoutPlan, WorkoutSetLog, WorkoutSessionState, ExerciseState)}
    before = snapshot()
    for route in ('/plan/generate-week', '/plan/next-week'):
        rejected = client.post(route, headers=headers, json={'target_days': 4})
        assert rejected.status_code == 409
        assert rejected.json()['detail']['code'] == 'customized_preview_required'
        assert rejected.json()['detail']['path'] == '/customize'
        assert snapshot() == before


@pytest.mark.parametrize('program_id', ['full_body_v1', 'adaptive_full_body_gold_v0_1'])
def test_authored_profile_cannot_silently_switch_to_generated_via_template_override(program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email='authored-no-implicit-customized@example.com')
    _upsert_profile(client, headers=headers, selected_program_id='pure_bodybuilding_phase_1_full_body', days_available=3)
    before = client.get('/profile', headers=headers).json()
    rejected = client.post('/plan/generate-week', headers=headers, json={'template_id': program_id, 'target_days': 4})
    assert rejected.status_code == 409
    assert rejected.json()['detail']['code'] == 'customized_preview_required'
    assert rejected.json()['detail']['path'] == '/customize'
    assert client.get('/profile', headers=headers).json() == before
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).count() == 0
        assert db.query(WorkoutSetLog).count() == 0
