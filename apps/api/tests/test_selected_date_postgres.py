"""Opt-in PostgreSQL selected-date races; never use inherited application DBs.

Run after Alembic 0021 on the explicitly verified disposable M2B PostgreSQL
container. Each test inserts a unique synthetic user and retains its records;
there is no schema creation, truncation, deletion or production fallback here.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import os
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


explicit_url = os.environ.get("TEST_DATABASE_URL")
if os.environ.get("M2B_POSTGRES_ISOLATED") != "1" or not explicit_url:
    pytest.skip("Requires explicitly verified disposable M2B PostgreSQL", allow_module_level=True)
target = make_url(explicit_url)
if target.get_backend_name() != "postgresql":
    pytest.skip("SQLite cannot qualify PostgreSQL locking", allow_module_level=True)
assert os.environ.get("DATABASE_URL") == explicit_url
assert target.drivername == "postgresql+psycopg"
assert (target.host, target.port, target.database, target.username) == (
    "127.0.0.1", 25461, "m2b_qualification", "m2b_test")
# Verify the target before importing the application or binding its engine.
probe_engine = create_engine(target)
with probe_engine.connect() as connection:
    identity = connection.execute(text(
        "SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()"
    )).one()
    assert tuple(identity[:2]) == ("m2b_qualification", "m2b_test")
    assert identity[2] is not None and identity[3] == 5432
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
        "0021_selected_workout_dates")
probe_engine.dispose()

from fastapi.testclient import TestClient
from app.database import SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.routers import workout
from app.security import create_access_token
from app import selected_date_plans


def _monday():
    today = datetime.now(UTC).astimezone(ZoneInfo("America/New_York")).date()
    return today - timedelta(days=today.weekday())


def _dates(offsets=(1, 4, 6), revision=0):
    monday = _monday()
    return {"template_id": "pure_bodybuilding_phase_1_full_body",
        "week_start": monday.isoformat(), "timezone": "America/New_York",
        "selected_dates": [(monday + timedelta(days=offset)).isoformat() for offset in offsets],
        "target_days": len(offsets), "expected_placement_revision": revision}


def _post(headers, path, payload):
    # No TestClient lifespan: migration owns the already-verified schema.
    client = TestClient(app)
    try:
        return client.post(path, headers=headers, json=payload)
    finally:
        client.close()


@pytest.fixture
def pg_scenario():
    assert engine.url == target and engine.dialect.name == "postgresql"
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f"{uuid4()}@example.invalid", name="Synthetic PG date race",
            password_hash="not-a-login", split_preference="full_body",
            selected_program_id="pure_bodybuilding_phase_1_full_body", days_available=5,
            equipment_profile=["dumbbell", "barbell", "bench", "cable", "machine"],
            nutrition_phase="maintenance"))
        db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}
    response = _post(headers, "/plan/generate-week", _dates())
    assert response.status_code == 200, response.text
    return user_id, headers, response.json()


def test_two_same_revision_requests_have_one_winner(pg_scenario, monkeypatch):
    user_id, headers, initial = pg_scenario
    attempts = Barrier(2)
    original_lock = selected_date_plans.lock_history_user

    def simultaneous_lock(db, locked_user_id):
        assert locked_user_id == user_id
        attempts.wait(timeout=10)
        original_lock(db, locked_user_id)

    monkeypatch.setattr(selected_date_plans, "lock_history_user", simultaneous_lock)
    requests = [_dates((0, 2, 5), 1), _dates((0, 3, 6), 1)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda payload: _post(headers, "/plan/generate-week", payload), requests))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(response.json() for response in responses if response.status_code == 200)
    assert winner["schedule"]["placement_revision"] == 2
    assert [s["exercises"] for s in winner["sessions"]] == [s["exercises"] for s in initial["sessions"]]
    assert [s["workout_occurrence_id"] for s in winner["sessions"]] == [
        s["workout_occurrence_id"] for s in initial["sessions"]]
    with SessionLocal() as db:
        rows = db.query(WorkoutPlan).filter_by(user_id=user_id).all()
        assert len(rows) == 1
        assert rows[0].placement_revision == 2
        assert rows[0].payload["schedule"] == winner["schedule"]
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 0
    loser = next(response for response in responses if response.status_code == 409)
    assert "placement revision" in loser.json()["detail"]


def _run_lock_order(first, second, first_lock, second_lock, user_id, monkeypatch):
    """Observe the second backend waiting on PostgreSQL before releasing first."""
    acquired, attempted, release = Event(), Event(), Event()
    second_backend = {}
    first_module, first_name = first_lock
    second_module, second_name = second_lock
    original_first = getattr(first_module, first_name)
    original_second = getattr(second_module, second_name)

    def hold_first(db, locked_user_id):
        assert locked_user_id == user_id
        original_first(db, locked_user_id)
        acquired.set()
        assert release.wait(timeout=15), "First transaction was not released"

    def wait_second(db, locked_user_id):
        assert locked_user_id == user_id
        assert acquired.wait(timeout=10)
        second_backend["pid"] = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
        attempted.set()
        original_second(db, locked_user_id)

    monkeypatch.setattr(first_module, first_name, hold_first)
    monkeypatch.setattr(second_module, second_name, wait_second)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first)
        try:
            assert acquired.wait(timeout=10), "First command never acquired its user lock"
            second_future = pool.submit(second)
            assert attempted.wait(timeout=10), "Second command never attempted its user lock"
            observed_wait = False
            deadline = monotonic() + 5
            while monotonic() < deadline:
                with engine.connect() as connection:
                    wait_type = connection.execute(text(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"
                    ), {"pid": second_backend["pid"]}).scalar_one_or_none()
                if wait_type == "Lock":
                    observed_wait = True
                    break
                sleep(0.01)
            assert observed_wait, "Second command did not serialize on PostgreSQL"
        finally:
            release.set()
        return first_future.result(timeout=15), second_future.result(timeout=15)


@pytest.mark.parametrize("first_action", ["log", "reschedule"])
def test_logging_and_rescheduling_serialize_without_rewriting_snapshot(pg_scenario, monkeypatch, first_action):
    user_id, headers, initial = pg_scenario
    session = initial["sessions"][0]
    exercise = session["exercises"][0]
    log_path = f"/workout/{session['workout_occurrence_id']}/log-set"
    log_payload = {"command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"],
        "set_index": 1, "reps": 8, "weight": 25}
    revised = _dates((0, 2, 5), 1)
    log = lambda: _post(headers, log_path, log_payload)
    reschedule = lambda: _post(headers, "/plan/generate-week", revised)
    log_lock = (workout, "_lock_history_user")
    reschedule_lock = (selected_date_plans, "lock_history_user")
    if first_action == "log":
        logged, scheduled = _run_lock_order(log, reschedule, log_lock, reschedule_lock, user_id, monkeypatch)
        assert scheduled.status_code == 409, scheduled.text
        assert "execution or consent snapshot" in scheduled.json()["detail"]
        retained = initial
        expected_revision = 1
    else:
        scheduled, logged = _run_lock_order(reschedule, log, reschedule_lock, log_lock, user_id, monkeypatch)
        assert scheduled.status_code == 200, scheduled.text
        retained = scheduled.json()
        expected_revision = 2
        assert retained["schedule"]["selected_dates"] == revised["selected_dates"]
        assert [s["exercises"] for s in retained["sessions"]] == [s["exercises"] for s in initial["sessions"]]
    assert logged.status_code == 200, logged.text
    assert logged.json()["workout_occurrence_id"] == session["workout_occurrence_id"]
    assert logged.json()["exercise_occurrence_id"] == exercise["exercise_occurrence_id"]
    with SessionLocal() as db:
        plan = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        occurrence = db.query(WorkoutOccurrence).filter_by(user_id=user_id).one()
        entry = db.query(WorkoutSetLog).filter_by(user_id=user_id).one()
        assert plan.placement_revision == expected_revision
        assert plan.payload["schedule"]["selected_dates"] == retained["schedule"]["selected_dates"]
        assert occurrence.placement_revision == expected_revision
        assert occurrence.scheduled_date.isoformat() == retained["sessions"][0]["scheduled_date"]
        assert occurrence.payload["scheduled_date"] == retained["sessions"][0]["scheduled_date"]
        assert occurrence.schedule_timezone == "America/New_York"
        assert entry.workout_occurrence_id == session["workout_occurrence_id"]
        assert entry.exercise_occurrence_id == exercise["exercise_occurrence_id"]
        assert entry.reps == 8 and entry.weight == 25 and entry.rpe is None
        frozen = occurrence.payload["exercises"][0]
        for field in ("id", "sets", "authored_prescription", "source_lineage", "source_relationships"):
            assert frozen[field] == exercise[field]
    # Remove synchronization wrappers before checking a late retry and freeze.
    monkeypatch.undo()
    retry = _post(headers, log_path, log_payload)
    assert retry.status_code == 200 and retry.json() == logged.json()
    blocked = _post(headers, "/plan/generate-week", _dates((0, 3, 6), expected_revision))
    assert blocked.status_code == 409
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 1
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).one().placement_revision == expected_revision
