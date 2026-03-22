from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_authored_generated_path_regression")

from app.database import Base, engine
from app.main import app
from app.program_loader import load_program_template


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
    _assert_authored_program_floor(payload, program_id="pure_bodybuilding_phase_1_full_body")
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
    _assert_authored_program_floor(payload, program_id="pure_bodybuilding_phase_2_full_body")
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
    headers = _register(client, email="history-isolation@example.com")

    _upsert_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        days_available=3,
    )
    generated_payload = _generate_week(client, headers=headers)
    assert generated_payload["program_template_id"] == "full_body_v1"

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
