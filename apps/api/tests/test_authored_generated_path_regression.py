from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import uuid
from typing import Any

from fastapi.testclient import TestClient
import pytest

from test_db import configure_test_database

configure_test_database("test_authored_generated_path_regression")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan
from app.program_loader import load_program_template, resolve_selected_program_binding_id
from app.routers import plan as plan_router
from core_engine.scheduler import AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY


TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"
PHASE1_MERGED_DAY1_IDS = [
    "cross_body_lat_pull_around",
    "low_incline_smith_machine_press",
    "machine_hip_adduction",
    "leg_press",
    "lying_paused_rope_face_pull",
    "cable_crunch",
    "seated_db_shoulder_press",
    "paused_barbell_rdl",
    "chest_supported_machine_row",
    "hammer_preacher_curl",
    "cuffed_behind_the_back_lateral_raise",
    "overhead_cable_triceps_extension_bar",
]
PHASE2_MERGED_DAY1_IDS = [
    "wide_grip_pull_up",
    "flat_machine_chest_press",
    "glute_ham_raise",
    "leg_extension",
    "meadows_incline_db_lateral_raise",
    "standing_calf_raise",
    "seated_leg_curl",
    "bottom_half_smith_machine_squat",
    "chest_supported_machine_row",
    "bottom_half_seated_cable_flye",
    "machine_hip_abduction",
    "overhead_cable_triceps_extension_bar",
]


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
            "weak_areas": ["chest", "hamstrings"],
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
    kept_ids = [
        "low_incline_smith_machine_press",
        "leg_press",
        "seated_db_shoulder_press",
        "chest_supported_machine_row",
        "hammer_preacher_curl",
    ]
    exercise_lookup = {
        _exercise_id(exercise): deepcopy(exercise)
        for exercise in stale["sessions"][0]["exercises"]
        if _exercise_id(exercise)
    }
    stale["sessions"][0]["exercises"] = [exercise_lookup[exercise_id] for exercise_id in kept_ids]
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
    expected_day1_ids: list[str],
    expected_session_set_totals: list[int],
) -> None:
    _assert_authored_program_floor(payload, program_id=program_id)
    assert [session["title"] for session in payload["sessions"]] == [
        "Full Body #1 + Full Body #2",
        "Full Body #3 + Full Body #4",
        "Arms & Weak Points",
    ]
    assert _session_primary_ids(payload["sessions"][0]) == expected_day1_ids
    assert [_session_set_total(session) for session in payload["sessions"]] == expected_session_set_totals


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
        expected_day1_ids=PHASE1_MERGED_DAY1_IDS,
        expected_session_set_totals=[34, 36, 18],
    )
    assert payload["mesocycle"]["authored_week_role"] == "adaptation"
    assert payload["mesocycle"]["is_deload_week"] is False


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
        expected_day1_ids=PHASE1_MERGED_DAY1_IDS,
        expected_session_set_totals=[34, 36, 18],
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
        expected_day1_ids=PHASE1_MERGED_DAY1_IDS,
        expected_session_set_totals=[34, 36, 18],
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
        expected_day1_ids=PHASE2_MERGED_DAY1_IDS,
        expected_session_set_totals=[26, 26, 15],
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
        expected_day1_ids=PHASE2_MERGED_DAY1_IDS,
        expected_session_set_totals=[26, 26, 15],
    )


def test_fresh_onboarding_generated_path_resolves_to_generated_family() -> None:
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

    payload = _generate_week(client, headers=headers)
    runtime_trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]

    assert payload["program_template_id"] == "full_body_v1"
    assert payload["template_selection_trace"]["selected_template_id"] == "full_body_v1"
    assert runtime_trace["activation_guard_matched"] is True
    assert runtime_trace["compatibility_selected_template_id"] == "full_body_v1"


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
    generated_payload = _generate_week(client, headers=headers)
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

    assert captured_scheduler_sessions == [
        {"name": "Full Body #1 + Full Body #2", "exercise_ids": PHASE1_MERGED_DAY1_IDS, "set_total": 34},
        {
            "name": "Full Body #3 + Full Body #4",
            "exercise_ids": [
                "assisted_pull_up",
                "paused_assisted_dip",
                "seated_leg_curl",
                "leg_extension",
                "cable_paused_shrug_in",
                "roman_chair_leg_raise",
                "lying_leg_curl",
                "hack_squat",
                "bent_over_cable_pec_flye",
                "neutral_grip_lat_pulldown",
                "leg_press_calf_press",
                "cable_reverse_flye_mechanical_dropset",
            ],
            "set_total": 36,
        },
        {
            "name": "Arms & Weak Points",
            "exercise_ids": [
                "weak_point_exercise_1",
                "weak_point_exercise_2_optional",
                "bayesian_cable_curl",
                "triceps_pressdown_bar",
                "bottom_2_3_constant_tension_preacher_curl",
                "cable_triceps_kickback",
                "standing_calf_raise",
            ],
            "set_total": 18,
        },
    ]
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
        generated_payload = _generate_week(client, headers=headers)
    finally:
        plan_router.generate_week_plan = original_generate_week_plan

    assert captured_flags == [True, False]
    assert "generated_full_body_runtime_trace" not in authored_payload["template_selection_trace"]
    assert generated_payload["template_selection_trace"]["generated_full_body_runtime_trace"]["activation_guard_matched"] is True


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
        expected_day1_ids=PHASE1_MERGED_DAY1_IDS,
        expected_session_set_totals=[34, 36, 18],
    )

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    assert today_payload["mesocycle"]["week_index"] == 1
    assert today_payload["mesocycle"]["authored_week_index"] == 1
    assert _session_primary_ids(today_payload) == PHASE1_MERGED_DAY1_IDS
    assert _session_set_total(today_payload) == 34
    assert int(today_payload.get("total_sets") or 0) == 34

    progress = client.get(f"/workout/{today_payload['session_id']}/progress", headers=headers)
    assert progress.status_code == 200
    progress_payload = progress.json()
    assert progress_payload["planned_total"] == 34
    assert [item["exercise_id"] for item in progress_payload["exercises"]] == PHASE1_MERGED_DAY1_IDS
    assert sum(int(item["planned_sets"]) for item in progress_payload["exercises"]) == 34

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
        assert _session_primary_ids(persisted_payload["sessions"][0]) == PHASE1_MERGED_DAY1_IDS
        assert _session_set_total(persisted_payload["sessions"][0]) == 34


@pytest.mark.parametrize(
    ("selected_program_id", "expected_total_sets"),
    [
        ("pure_bodybuilding_phase_1_full_body", 34),
        ("pure_bodybuilding_phase_2_full_body", 26),
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


def test_current_week_regenerate_keeps_displayed_and_authored_week_indices() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="regenerate-current-week@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )

    first = _generate_week(client, headers=headers)
    regenerated = _generate_week(client, headers=headers)

    assert regenerated["mesocycle"]["week_index"] == first["mesocycle"]["week_index"]
    assert regenerated["mesocycle"]["authored_week_index"] == first["mesocycle"]["authored_week_index"]


def test_next_week_advance_increments_week_index() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register(client, email="advance-next-week@example.com")
    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        days_available=3,
    )

    current_week = _generate_week(client, headers=headers)
    next_week_response = client.post("/plan/next-week", headers=headers, json={})
    assert next_week_response.status_code == 200
    next_week_payload = next_week_response.json()

    assert int(next_week_payload["mesocycle"]["week_index"]) == int(current_week["mesocycle"]["week_index"]) + 1


@pytest.mark.parametrize(
    "switch_template_id",
    ["pure_bodybuilding_phase_2_full_body", "full_body_v1"],
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
        expected_day1_ids=PHASE2_MERGED_DAY1_IDS,
        expected_session_set_totals=[26, 26, 15],
    )
