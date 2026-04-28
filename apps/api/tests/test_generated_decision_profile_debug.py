from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_generated_decision_profile_debug")

from app.database import Base, engine
from app.database import SessionLocal
from app.main import app
from app.models import User
from app.routers import plan as plan_router


TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


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
    days_available: int,
    session_time_budget_minutes: int | None = None,
    near_failure_tolerance: str | None = None,
    movement_restrictions: list[str] | None = None,
    onboarding_answers: dict | None = None,
) -> None:
    payload = {
        "name": "Debug User",
        "age": 30,
        "weight": 82,
        "gender": "male",
        "split_preference": split_preference,
        "selected_program_id": selected_program_id,
        "program_selection_mode": "auto" if selected_program_id == "full_body_v1" else "manual",
        "training_location": "gym",
        "equipment_profile": ["barbell", "bench", "dumbbell", "machine"],
        "weak_areas": ["chest"],
        "days_available": days_available,
        "nutrition_phase": "maintenance",
        "calories": 2600,
        "protein": 180,
        "fat": 70,
        "carbs": 280,
        "onboarding_answers": onboarding_answers or {},
    }
    if session_time_budget_minutes is not None:
        payload["session_time_budget_minutes"] = session_time_budget_minutes
    if near_failure_tolerance is not None:
        payload["near_failure_tolerance"] = near_failure_tolerance
    if movement_restrictions is not None:
        payload["movement_restrictions"] = movement_restrictions
    response = client.post("/profile", headers=headers, json=payload)
    assert response.status_code == 200


def test_generated_debug_payload_includes_expected_fields() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-debug-fields@example.com", name="Generated Debug Fields")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )

    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    expected = {
        "selected_program_id",
        "path_family",
        "target_days",
        "session_time_band",
        "recovery_modifier",
        "training_status",
        "detraining_status",
        "goal_mode",
        "equipment_scope",
        "weakpoint_targets",
        "movement_restriction_flags",
        "generated_mode",
        "reentry_required",
        "decision_trace",
    }
    assert expected <= set(payload.keys())
    assert "defaults_applied" in payload["decision_trace"]
    assert "missing_fields" in payload["decision_trace"]


def test_sparse_legacy_generated_user_gets_safe_defaults_and_trace() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-debug-sparse@example.com", name="Generated Debug Sparse")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "generated-debug-sparse@example.com").first()
        assert user is not None
        user.days_available = None
        user.session_time_budget_minutes = None
        user.onboarding_answers = {}
        session.commit()

    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["target_days"] == 3
    assert payload["decision_trace"]["defaults_applied"]
    assert payload["decision_trace"]["missing_fields"]


def test_authored_selected_user_reports_authored_path_and_does_not_call_generated_constructor(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    def _unexpected_constructor(*args, **kwargs):
        raise AssertionError("Generated constructor should not run for debug decision profile endpoint.")

    monkeypatch.setattr(plan_router, "prepare_generated_full_body_runtime_template", _unexpected_constructor)
    headers = _register_user(client, email="generated-debug-authored@example.com", name="Generated Debug Authored")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        split_preference="full_body",
        days_available=5,
    )

    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["path_family"] == "authored"


def test_low_time_user_reports_low_time_mode() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-debug-low-time@example.com", name="Generated Debug Low Time")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        session_time_budget_minutes=40,
    )
    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    assert response.json()["generated_mode"] == "low_time_full_body"


def test_low_recovery_user_reports_low_recovery_mode() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-debug-low-recovery@example.com", name="Generated Debug Low Recovery")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        near_failure_tolerance="low",
    )
    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    assert response.json()["generated_mode"] == "low_recovery_full_body"


def test_detrained_user_reports_comeback_reentry() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-debug-detrained@example.com", name="Generated Debug Detrained")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        onboarding_answers={"trained_consistently_last_4_weeks": False},
    )
    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_mode"] == "comeback_reentry"
    assert payload["reentry_required"] is True


def test_sensitive_free_text_restrictions_do_not_appear_in_debug_or_logs(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    captured: list[dict] = []

    def _capture_log(event: str, level: str = "info", **fields):
        captured.append({"event": event, "fields": fields})

    monkeypatch.setattr(plan_router, "log_event", _capture_log)

    headers = _register_user(client, email="generated-debug-sensitive@example.com", name="Generated Debug Sensitive")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        movement_restrictions=["recent shoulder surgery requiring caution"],
    )
    response = client.get("/plan/generated-decision-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["movement_restriction_flags"] == ["other"]
    assert "surgery" not in str(payload).lower()

    debug_log = next(item for item in captured if item["event"] == "generated_decision_profile_debug_viewed")
    assert "movement_restriction_flags" not in debug_log["fields"]
    assert int(debug_log["fields"]["movement_restriction_count"]) == 1


def test_generated_decision_profile_resolved_log_contains_expected_structured_fields(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    captured: list[dict] = []

    def _capture_log(event: str, level: str = "info", **fields):
        captured.append({"event": event, "fields": fields})

    monkeypatch.setattr(plan_router, "log_event", _capture_log)

    headers = _register_user(client, email="generated-debug-log-fields@example.com", name="Generated Debug Log Fields")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        movement_restrictions=["Overhead pressing"],
    )
    response = client.post("/plan/generate-week", headers=headers, json={})
    assert response.status_code == 200

    resolved_log = next(item for item in captured if item["event"] == "generated_decision_profile_resolved")
    fields = resolved_log["fields"]
    expected_keys = {
        "user_id",
        "selected_program_id",
        "path_family",
        "generated_mode",
        "target_days",
        "session_time_band",
        "recovery_modifier",
        "training_status",
        "detraining_status",
        "goal_mode",
        "equipment_scope",
        "weakpoint_count",
        "movement_restriction_count",
        "defaults_applied",
        "missing_fields",
        "reentry_required",
        "insufficient_data_avoided",
    }
    assert expected_keys <= set(fields.keys())
    assert "movement_restriction_flags" not in fields
