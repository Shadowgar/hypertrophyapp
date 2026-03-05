from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_plan_guides_api")

from app.database import Base, engine
from app.main import app


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_guide_program_catalog_contract() -> None:
    _reset_db()
    client = TestClient(app)

    response = client.get("/plan/guides/programs")
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, list)
    full_body = next((item for item in payload if item["id"] == "full_body_v1"), None)
    assert full_body is not None
    assert "name" in full_body
    assert "split" in full_body
    assert "days_supported" in full_body


def test_program_guide_day_and_exercise_endpoints() -> None:
    _reset_db()
    client = TestClient(app)

    program = client.get("/plan/guides/programs/full_body_v1")
    assert program.status_code == 200
    program_payload = program.json()
    assert program_payload["id"] == "full_body_v1"
    assert len(program_payload["days"]) >= 1
    first_day = program_payload["days"][0]
    assert first_day["day_index"] == 1
    assert first_day["exercise_count"] >= 1

    day = client.get("/plan/guides/programs/full_body_v1/days/1")
    assert day.status_code == 200
    day_payload = day.json()
    assert day_payload["program_id"] == "full_body_v1"
    assert day_payload["day_index"] == 1
    assert len(day_payload["exercises"]) >= 1

    first_exercise_id = day_payload["exercises"][0]["id"]
    exercise = client.get(f"/plan/guides/programs/full_body_v1/exercise/{first_exercise_id}")
    assert exercise.status_code == 200
    exercise_payload = exercise.json()
    assert exercise_payload["program_id"] == "full_body_v1"
    assert exercise_payload["exercise"]["id"] == first_exercise_id


def test_program_guide_endpoint_404s_for_unknown_resources() -> None:
    _reset_db()
    client = TestClient(app)

    missing_program = client.get("/plan/guides/programs/does_not_exist")
    assert missing_program.status_code == 404

    missing_day = client.get("/plan/guides/programs/full_body_v1/days/999")
    assert missing_day.status_code == 404

    missing_exercise = client.get("/plan/guides/programs/full_body_v1/exercise/unknown_exercise")
    assert missing_exercise.status_code == 404
