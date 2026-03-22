from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_phase1_canonical_path_smoke")

from app.database import Base, engine
from app.main import app


CANONICAL_PROGRAM_ID = "pure_bodybuilding_phase_1_full_body"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_onboard(client: TestClient, *, selected_program_id: str = CANONICAL_PROGRAM_ID) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={
            "email": f"phase1-smoke-{selected_program_id}@example.com",
            "password": "Phase1Smoke1",
            "name": "Phase 1 Smoke",
        },
    )
    assert register.status_code == 200
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase 1 Smoke",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": selected_program_id,
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
            "weak_areas": ["chest", "hamstrings"],
            "days_available": 5,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    expected_program_id = "full_body_v1" if selected_program_id in {"full_body_v1", "adaptive_full_body_gold_v0_1"} else selected_program_id
    assert profile.json()["selected_program_id"] == expected_program_id
    return headers


def test_phase1_canonical_smoke_path_preserves_identity_and_session_continuity() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    generated_week = client.post("/plan/generate-week", headers=headers, json={})
    assert generated_week.status_code == 200
    week_payload = generated_week.json()

    assert week_payload["program_template_id"] == CANONICAL_PROGRAM_ID
    assert week_payload["template_selection_trace"]["selected_template_id"] == CANONICAL_PROGRAM_ID
    assert "generated_full_body_runtime_trace" not in week_payload["template_selection_trace"]
    assert len(week_payload["sessions"]) == 5
    assert all(session["session_id"].startswith(f"{CANONICAL_PROGRAM_ID}-") for session in week_payload["sessions"])

    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    today_payload = today.json()
    assert today_payload["session_id"].startswith(f"{CANONICAL_PROGRAM_ID}-")

    first_exercise = today_payload["exercises"][0]
    for required_field in (
        "id",
        "name",
        "sets",
        "rep_range",
        "recommended_working_weight",
        "movement_pattern",
        "primary_muscles",
        "primary_exercise_id",
        "substitution_candidates",
    ):
        assert required_field in first_exercise

    log_set = client.post(
        f"/workout/{today_payload['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": int(first_exercise["rep_range"][0]),
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert log_set.status_code == 200

    week_start = date.today() - timedelta(days=date.today().weekday())
    checkin = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": week_start.isoformat(),
            "body_weight": 82.0,
            "adherence_score": 4,
            "sleep_quality": 3,
            "stress_level": 2,
            "pain_flags": [],
            "notes": "canonical smoke check-in",
        },
    )
    assert checkin.status_code == 200

    weekly_review = client.post(
        "/weekly-review",
        headers=headers,
        json={
            "body_weight": 82.0,
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
            "adherence_score": 4,
            "notes": "canonical smoke weekly review",
        },
    )
    assert weekly_review.status_code == 200
    assert weekly_review.json()["status"] == "review_logged"

    history = client.get(
        f"/history/calendar?start_date={(date.today() - timedelta(days=7)).isoformat()}&end_date={date.today().isoformat()}",
        headers=headers,
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert any(CANONICAL_PROGRAM_ID in day["program_ids"] for day in history_payload["days"])

    apply_adaptation = client.post(
        "/plan/adaptation/apply",
        headers=headers,
        json={
            "program_id": CANONICAL_PROGRAM_ID,
            "target_days": 3,
            "duration_weeks": 2,
            "weak_areas": ["chest", "hamstrings"],
        },
    )
    assert apply_adaptation.status_code == 200
    assert apply_adaptation.json()["status"] == "applied"

    regenerate_week = client.post("/plan/generate-week", headers=headers, json={})
    assert regenerate_week.status_code == 200
    regenerated_payload = regenerate_week.json()

    assert regenerated_payload["program_template_id"] == CANONICAL_PROGRAM_ID
    assert len(regenerated_payload["sessions"]) == 3
    assert [session["title"] for session in regenerated_payload["sessions"]] == [
        "Full Body #1 + Full Body #2",
        "Full Body #3 + Full Body #4",
        "Arms & Weak Points",
    ]
    assert [
        sum(int(exercise.get("sets") or 0) for exercise in session["exercises"])
        for session in regenerated_payload["sessions"]
    ] == [34, 36, 18]
    assert all(
        session["session_id"].startswith(f"{CANONICAL_PROGRAM_ID}-")
        for session in regenerated_payload["sessions"]
    )
    assert regenerated_payload["applied_frequency_adaptation"]["target_days"] == 3
    assert "generated_full_body_runtime_trace" not in regenerated_payload["template_selection_trace"]

    training_state = client.get("/profile/training-state", headers=headers)
    assert training_state.status_code == 200
    user_program_state = training_state.json()["user_program_state"]
    assert user_program_state["program_id"] == CANONICAL_PROGRAM_ID
    assert user_program_state["session_id"].startswith(f"{CANONICAL_PROGRAM_ID}-")


@pytest.mark.parametrize("legacy_program_id", ["full_body_v1", "adaptive_full_body_gold_v0_1"])
def test_phase1_legacy_aliases_still_resolve_safely(legacy_program_id: str) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client, selected_program_id=legacy_program_id)

    generated_week = client.post("/plan/generate-week", headers=headers, json={})
    assert generated_week.status_code == 200

    payload = generated_week.json()
    assert payload["program_template_id"] == "full_body_v1"
    assert payload["template_selection_trace"]["selected_template_id"] == "full_body_v1"
    runtime_trace = payload["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert runtime_trace["generated_constructor_applied"] is True
    assert runtime_trace["content_origin"] == "generated_constructor_applied"
