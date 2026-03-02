import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

DB_FILE = Path(__file__).resolve().parent / "test_recovery_measurements.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from app.database import Base, engine
from app.main import app


def _auth_header(client: TestClient) -> dict[str, str]:
    email = f"recovery-{uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123", "name": "Recovery"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_soreness_and_body_measurement_crud() -> None:
    _reset_db()

    client = TestClient(app)
    headers = _auth_header(client)

    soreness_create = client.post(
        "/soreness",
        headers=headers,
        json={
            "entry_date": date(2026, 3, 2).isoformat(),
            "severity_by_muscle": {"quads": "moderate", "hamstrings": "mild"},
            "notes": "Leg day residual fatigue",
        },
    )
    assert soreness_create.status_code == 201
    soreness_id = soreness_create.json()["id"]

    soreness_update = client.put(
        f"/soreness/{soreness_id}",
        headers=headers,
        json={
            "entry_date": date(2026, 3, 2).isoformat(),
            "severity_by_muscle": {"quads": "severe"},
            "notes": "Adjusted",
        },
    )
    assert soreness_update.status_code == 200
    assert soreness_update.json()["severity_by_muscle"]["quads"] == "severe"

    soreness_list = client.get("/soreness", headers=headers)
    assert soreness_list.status_code == 200
    assert len(soreness_list.json()) == 1

    soreness_delete = client.delete(f"/soreness/{soreness_id}", headers=headers)
    assert soreness_delete.status_code == 204

    measurement_create = client.post(
        "/body-measurements",
        headers=headers,
        json={
            "measured_on": date(2026, 3, 2).isoformat(),
            "name": "waist",
            "value": 82.5,
            "unit": "cm",
        },
    )
    assert measurement_create.status_code == 201
    measurement_id = measurement_create.json()["id"]

    measurement_update = client.put(
        f"/body-measurements/{measurement_id}",
        headers=headers,
        json={"value": 82.0},
    )
    assert measurement_update.status_code == 200
    assert abs(measurement_update.json()["value"] - 82.0) < 1e-9

    measurement_list = client.get("/body-measurements", headers=headers)
    assert measurement_list.status_code == 200
    assert len(measurement_list.json()) == 1

    measurement_delete = client.delete(f"/body-measurements/{measurement_id}", headers=headers)
    assert measurement_delete.status_code == 204


def test_soreness_schema_rejects_invalid_severity() -> None:
    _reset_db()

    client = TestClient(app)
    headers = _auth_header(client)
    response = client.post(
        "/soreness",
        headers=headers,
        json={
            "entry_date": date(2026, 3, 2).isoformat(),
            "severity_by_muscle": {"quads": "extreme"},
        },
    )
    assert response.status_code == 422
