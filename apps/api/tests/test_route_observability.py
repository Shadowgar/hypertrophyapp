from __future__ import annotations

from datetime import date, timedelta
import json
import logging
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_route_observability")

from app.database import Base, engine
from app.main import app

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _json_logs(caplog) -> list[dict]:
    parsed: list[dict] = []
    for record in caplog.records:
        try:
            parsed.append(json.loads(record.message))
        except json.JSONDecodeError:
            continue
    return parsed


def _register_and_profile(client: TestClient, *, email: str, selected_program_id: str) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={"email": email, "password": TEST_CREDENTIAL, "name": "Observability User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Observability User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": selected_program_id,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell", "cable", "machine"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    return headers


def test_logging_captures_regenerate_current_and_next_week_advance(caplog) -> None:
    _reset_db()
    client = TestClient(app)
    caplog.set_level(logging.INFO, logger="hypertrophy.app")
    headers = _register_and_profile(client, email="logging-generate@example.com", selected_program_id="full_body_v1")

    caplog.clear()
    first_response = client.post("/plan/generate-week", headers=headers, json={"template_id": "full_body_v1"})
    assert first_response.status_code == 200
    first_payload = first_response.json()
    first_logs = _json_logs(caplog)
    assert any(
        entry.get("event") == "week_regenerated_current"
        and entry.get("generation_mode") == "current_week_regenerate"
        and entry.get("displayed_week_index") == 1
        for entry in first_logs
    )
    assert any(
        entry.get("event") == "generation_path_selected"
        and entry.get("path_family") == "generated"
        and entry.get("generation_mode") == "current_week_regenerate"
        for entry in first_logs
    )

    caplog.clear()
    next_response = client.post("/plan/next-week", headers=headers, json={"template_id": "full_body_v1"})
    assert next_response.status_code == 200
    next_payload = next_response.json()
    next_logs = _json_logs(caplog)
    assert date.fromisoformat(next_payload["week_start"]) == date.fromisoformat(first_payload["week_start"]) + timedelta(days=7)
    assert any(
        entry.get("event") == "week_advanced_next"
        and entry.get("generation_mode") == "next_week_advance"
        and entry.get("displayed_week_index") == 2
        for entry in next_logs
    )


def test_logging_captures_authored_route_choice(caplog) -> None:
    _reset_db()
    client = TestClient(app)
    caplog.set_level(logging.INFO, logger="hypertrophy.app")
    headers = _register_and_profile(
        client,
        email="logging-authored@example.com",
        selected_program_id="pure_bodybuilding_phase_1_full_body",
    )

    caplog.clear()
    response = client.post("/plan/generate-week", headers=headers, json={"target_days": 3})
    assert response.status_code == 200
    logs = _json_logs(caplog)
    assert any(
        entry.get("event") == "generation_path_selected"
        and entry.get("path_family") == "authored"
        and entry.get("generation_mode") == "current_week_regenerate"
        and entry.get("target_days") == 3
        for entry in logs
    )


def test_logging_captures_adaptation_preview_validation_failure(caplog) -> None:
    _reset_db()
    client = TestClient(app)
    caplog.set_level(logging.INFO, logger="hypertrophy.app")
    headers = _register_and_profile(
        client,
        email="logging-preview-validation@example.com",
        selected_program_id="pure_bodybuilding_phase_1_full_body",
    )

    caplog.clear()
    response = client.post(
        "/plan/adaptation/preview",
        headers=headers,
        json={"target_days": 3, "duration_weeks": 10},
    )
    assert response.status_code == 422
    logs = _json_logs(caplog)
    assert any(
        entry.get("event") == "frequency_adaptation_preview_failed_validation"
        and entry.get("route") == "/plan/adaptation/preview"
        and "Temporary duration must be between 1 and 8 weeks." in str(entry.get("error_message"))
        for entry in logs
    )
