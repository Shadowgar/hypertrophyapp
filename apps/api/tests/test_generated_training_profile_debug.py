from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_generated_training_profile_debug")

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
        "name": "Training Debug User",
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


def test_generated_training_debug_payload_includes_expected_top_level_fields() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-training-debug-fields@example.com", name="Generated Training Debug Fields")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )

    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    expected = {
        "selected_program_id",
        "path_family",
        "decision_profile",
        "runtime_active",
        "trace_only_controls",
        "decision_trace",
    }
    assert expected == set(payload.keys())


def test_generated_training_debug_runtime_active_only_contains_normalized_active_fields() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-training-debug-runtime-active@example.com", name="Generated Training Debug Runtime Active")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    runtime_active = payload["runtime_active"]
    assert set(runtime_active.keys()) == {
        "target_days",
        "session_time_band",
        "recovery_modifier",
        "weakpoint_targets",
        "movement_restriction_flags",
        "generated_mode",
    }
    assert "starting_rir" not in runtime_active
    assert "weekly_volume_band" not in runtime_active


def test_generated_training_debug_trace_only_controls_stay_outside_runtime_active() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-training-debug-trace-only@example.com", name="Generated Training Debug Trace Only")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    runtime_active = payload["runtime_active"]
    trace_only = payload["trace_only_controls"]
    assert "starting_rir" in trace_only
    assert "high_fatigue_cap" in trace_only
    assert "weekly_volume_band" in trace_only
    assert "starting_rir" not in runtime_active
    assert "high_fatigue_cap" not in runtime_active
    assert "weekly_volume_band" not in runtime_active


def test_generated_training_debug_sparse_legacy_user_gets_safe_defaults() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-training-debug-sparse@example.com", name="Generated Training Debug Sparse")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "generated-training-debug-sparse@example.com").first()
        assert user is not None
        user.days_available = None
        user.session_time_budget_minutes = None
        user.onboarding_answers = {}
        session.commit()

    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_active"]["target_days"] == 3
    assert payload["decision_trace"]["defaults_applied"]
    assert payload["decision_trace"]["missing_fields"]


def test_generated_training_debug_authored_user_reports_authored_path_without_generated_runtime(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    def _unexpected_constructor(*args, **kwargs):
        raise AssertionError("Generated constructor should not run for training debug endpoint.")

    monkeypatch.setattr(plan_router, "prepare_generated_full_body_runtime_template", _unexpected_constructor)
    headers = _register_user(client, email="generated-training-debug-authored@example.com", name="Generated Training Debug Authored")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        split_preference="full_body",
        days_available=5,
    )

    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["path_family"] == "authored"


def test_generated_training_profile_debug_route_requires_auth() -> None:
    _reset_db()
    client = TestClient(app)
    response = client.get("/plan/generated-training-profile/debug")
    assert response.status_code == 403


def test_generated_training_profile_debug_route_respects_dev_guard(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(client, email="generated-training-debug-guard@example.com", name="Generated Training Debug Guard")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
    )
    monkeypatch.setattr(plan_router.settings, "allow_dev_wipe_endpoints", False)
    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Debug endpoints disabled"


def test_sensitive_free_text_restrictions_do_not_appear_in_training_debug_or_logs(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    captured: list[dict] = []

    def _capture_log(event: str, level: str = "info", **fields):
        captured.append({"event": event, "fields": fields})

    monkeypatch.setattr(plan_router, "log_event", _capture_log)
    headers = _register_user(client, email="generated-training-debug-sensitive@example.com", name="Generated Training Debug Sensitive")
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        movement_restrictions=["recent shoulder surgery requiring caution"],
    )

    response = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_active"]["movement_restriction_flags"] == ["other"]
    assert "surgery" not in str(payload).lower()

    debug_log = next(item for item in captured if item["event"] == "generated_training_profile_debug_viewed")
    assert "movement_restrictions" not in debug_log["fields"]
    assert "movement_restriction_flags" not in debug_log["fields"]


def test_generated_training_profile_resolved_log_contains_expected_structured_fields(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)
    captured: list[dict] = []

    def _capture_log(event: str, level: str = "info", **fields):
        captured.append({"event": event, "fields": fields})

    monkeypatch.setattr(plan_router, "log_event", _capture_log)

    headers = _register_user(client, email="generated-training-debug-log-fields@example.com", name="Generated Training Debug Log Fields")
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

    resolved_log = next(item for item in captured if item["event"] == "generated_training_profile_resolved")
    fields = resolved_log["fields"]
    expected_keys = {
        "user_id",
        "selected_program_id",
        "path_family",
        "generated_mode",
        "target_days",
        "session_time_band",
        "recovery_modifier",
        "goal_mode",
        "training_status",
        "weekly_volume_band",
        "starting_rir",
        "high_fatigue_cap",
        "weakpoint_count",
        "defaults_applied",
        "missing_fields",
        "missing_fields_count",
        "trace_only_fields",
        "runtime_active_fields",
    }
    assert expected_keys <= set(fields.keys())
    assert "movement_restriction_flags" not in fields


def test_generated_training_profile_debug_output_is_deterministic_for_same_user() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-training-debug-deterministic@example.com",
        name="Generated Training Debug Deterministic",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        session_time_budget_minutes=60,
        movement_restrictions=["Overhead pressing"],
    )

    first = client.get("/plan/generated-training-profile/debug", headers=headers)
    second = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_generated_training_debug_reflects_generated_path_after_non_destructive_program_selection_update() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_user(
        client,
        email="generated-training-debug-selection-update@example.com",
        name="Generated Training Debug Selection Update",
    )
    _post_profile(
        client,
        headers=headers,
        selected_program_id="pure_bodybuilding_phase_1_full_body",
        split_preference="full_body",
        days_available=3,
    )

    update = client.post(
        "/profile/program-selection",
        headers=headers,
        json={"selected_program_id": "full_body_v1", "program_selection_mode": "manual"},
    )
    assert update.status_code == 200
    updated_profile = update.json()
    assert updated_profile["selected_program_id"] == "full_body_v1"

    debug = client.get("/plan/generated-training-profile/debug", headers=headers)
    assert debug.status_code == 200
    debug_payload = debug.json()
    assert debug_payload["path_family"] == "generated"
    assert debug_payload["selected_program_id"] == "full_body_v1"
