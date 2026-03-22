from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_authored_generated_path_regression")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import WorkoutPlan
from app.program_loader import load_program_template
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
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert response.status_code == 200
    return response.json()


def _generate_week(client: TestClient, *, headers: dict[str, str]) -> dict:
    response = client.post("/plan/generate-week", headers=headers, json={})
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
