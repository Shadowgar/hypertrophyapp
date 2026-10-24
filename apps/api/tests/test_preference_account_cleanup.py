"""Development account cleanup preserves gates and handles presentation FKs.

The runner must select an explicit disposable database before app imports.
Accounts are unique per test; no reset helper or shared fixture deletion is used.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, UserInterfacePreference, WorkoutSetLog, AuthoredInitialCalibration


@pytest.fixture
def accounts():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    def register():
        email = f"preference-cleanup-{uuid4()}@example.com"
        response = client.post("/auth/register", json={
            "email": email, "password": "Synthetic-cleanup-only-Q98z!", "name": "Cleanup fixture"})
        assert response.status_code == 200
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        saved = client.put("/profile/preferences", headers=headers, json={
            "theme_family": "graphite", "appearance": "system", "weight_unit": "kg", "expected_revision": 0})
        assert saved.status_code == 200
        with SessionLocal() as db:
            user_id = db.query(User).filter_by(email=email).one().id
            db.add(WorkoutSetLog(user_id=user_id, workout_id="cleanup-fixture", primary_exercise_id="fixture",
                exercise_id="fixture", set_index=1, reps=8, weight=20))
            db.add(AuthoredInitialCalibration(user_id=user_id, revision=1, command_id=str(uuid4()),
                command_digest="0" * 64, source_scope="1" * 64, setup_scope="2" * 64,
                workout_occurrence_id="synthetic-retained-provenance", exercise_occurrence_id="synthetic-exercise",
                data={"method": "known_1rm", "load": 30, "unit": "kg"}, load_context={"basis": "per_hand"}))
            db.commit()
        return user_id, email, headers, saved.json()

    return client, register(), register()


def assert_retained(client, account):
    user_id, _, headers, saved = account
    assert client.get("/profile/preferences", headers=headers).json() == saved
    with SessionLocal() as db:
        assert db.get(User, user_id) is not None
        assert db.query(AuthoredInitialCalibration).filter_by(user_id=user_id).count() == 1
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 1


@pytest.mark.parametrize("route", ["profile", "auth"])
def test_development_account_wipe_removes_preferences_only_for_the_target(accounts, monkeypatch, route):
    client, target, other = accounts
    user_id, email, headers, _ = target

    def wipe(confirmation="WIPE"):
        if route == "profile":
            return client.post("/profile/dev/wipe", headers=headers)
        return client.post("/auth/dev/wipe-user", json={"email": email, "confirmation": confirmation})

    monkeypatch.delenv("ALLOW_DEV_WIPE_ENDPOINTS", raising=False)
    assert Settings(_env_file=None).allow_dev_wipe_endpoints is False
    monkeypatch.setattr(settings, "allow_dev_wipe_endpoints", False)
    assert wipe().status_code == 403
    assert_retained(client, target)
    assert_retained(client, other)

    monkeypatch.setattr(settings, "allow_dev_wipe_endpoints", True)
    if route == "auth":
        assert wipe("decline").status_code == 400
        assert_retained(client, target)
    else:
        assert client.post("/profile/dev/wipe").status_code == 401
        assert_retained(client, target)
    response = wipe()
    assert response.status_code == 200
    assert response.json() == {"status": "wiped"}
    with SessionLocal() as db:
        assert db.get(UserInterfacePreference, user_id) is None
        assert db.get(User, user_id) is None
        assert db.query(AuthoredInitialCalibration).filter_by(user_id=user_id).count() == 0
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 0
    assert client.get("/profile/preferences", headers=headers).status_code == 401
    assert_retained(client, other)
    if route == "auth":
        assert wipe().json() == {"status": "already_absent"}


def test_development_training_reset_preserves_account_preferences(accounts, monkeypatch):
    client, target, other = accounts
    user_id, _, headers, saved = target
    monkeypatch.setattr(settings, "allow_dev_wipe_endpoints", True)
    response = client.post("/profile/dev/reset-phase1", headers=headers)
    assert response.status_code == 200
    assert client.get("/profile/preferences", headers=headers).json() == saved
    with SessionLocal() as db:
        assert db.get(User, user_id) is not None
        assert db.query(AuthoredInitialCalibration).filter_by(user_id=user_id).count() == 1
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 0
    assert_retained(client, other)
