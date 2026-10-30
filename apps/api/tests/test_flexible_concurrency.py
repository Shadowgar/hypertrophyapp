"""Real same-account PostgreSQL races, opt-in on a verified synthetic target."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import os
from pathlib import Path
from threading import Barrier, Event
import time
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.skipif(os.environ.get("FLEXIBLE_CONCURRENCY_POSTGRES") != "1",
    reason="Requires explicitly verified disposable PostgreSQL concurrency target")


@pytest.fixture(scope="module")
def verified_target():
    from app.database import engine
    target = make_url(os.environ["TEST_DATABASE_URL"])
    assert target.get_backend_name() == "postgresql" and not target.query
    assert os.environ.get("TEST_DATABASE_DISPOSABLE") == "1"
    assert target.host == "127.0.0.1" and target.port != 5432 and target.port == int(os.environ["TEST_DATABASE_PORT"])
    assert target.username == os.environ["TEST_DATABASE_USER"] == "flexible_migration_test"
    assert target.database == os.environ["TEST_DATABASE_NAME"] and target.database.startswith("flexible_concurrency_qualification_")
    assert engine.url == target and os.environ["DATABASE_URL"] == os.environ["TEST_DATABASE_URL"]
    with engine.connect() as connection:
        assert tuple(connection.execute(sa.text("SELECT current_database(),current_user")).one()) == (target.database, target.username)
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0027_flexible_training"
    return engine


@pytest.fixture
def account(verified_target, monkeypatch):
    from fastapi.testclient import TestClient
    from test_flexible_lifecycle import small_source
    from app.database import SessionLocal
    from app.main import app
    from app.models import User
    from auth_test_helpers import create_access_token
    small_source(monkeypatch)
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f"{uuid4()}@example.invalid", name="Synthetic PostgreSQL concurrency",
            password_hash="synthetic-not-a-login", split_preference="full_body",
            selected_program_id="pure_bodybuilding_phase_1_full_body", program_selection_mode="manual", days_available=5,
            equipment_profile=["dumbbell", "barbell", "bench", "cable", "machine"], nutrition_phase="maintenance"))
        db.commit()
    client = TestClient(app)
    yield user_id, {"Authorization": f"Bearer {create_access_token(user_id)}"}, client
    client.close()


def _enrollment_request(client, headers):
    body = {"program_id": "pure_bodybuilding_phase_1_full_body", "timezone": "America/New_York", "expected_sessions_per_week": 3}
    response = client.post("/training/enroll/preview", headers=headers, json=body)
    assert response.status_code == 200 and response.json()["available"], response.text
    return {**body, "preview_digest": response.json()["digest"], "confirmed": True, "command_id": str(uuid4())}


def _enroll(client, headers):
    response = client.post("/training/enroll", headers=headers, json=_enrollment_request(client, headers))
    assert response.status_code == 200, response.text
    return response.json()


def _command(state, **changes):
    return {"command_id": str(uuid4()), "expected_revision": state["revision"],
        "occurrence_id": state["occurrence_id"], "expected_digest": state["digest"],
        "expected_local_day": state["local_day"], "confirmed": True, **changes}


def _record(name, backend_pids, replies):
    output = Path(os.environ["FLEXIBLE_CONCURRENCY_EVIDENCE"]).resolve()
    assert output.is_relative_to(Path(os.environ["CI_TEST_ROOT"]).resolve(strict=True))
    with output.open("a") as file:
        file.write(json.dumps({"case": name, "waiting_backend_pids": backend_pids,
            "response_statuses": [reply.status_code for reply in replies]}) + "\n")


def _race(engine, user_id, headers, requests, *, queued_first=None):
    """Queue both real HTTP commands behind one owned row, then release them."""
    from app.main import app
    from app.models import User
    from fastapi.testclient import TestClient
    barrier = Barrier(len(requests) + 1)
    second_gate = Event()
    if queued_first is None:
        second_gate.set()

    def post(index, path, body):
        client = TestClient(app)
        try:
            barrier.wait(timeout=10)
            if queued_first is not None and index != queued_first:
                assert second_gate.wait(timeout=15), "First command must enter the actual database lock queue"
            return client.post(path, headers=headers, json=body)
        finally:
            client.close()

    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=len(requests)) as pool:
        transaction = blocker.begin()
        blocker.execute(sa.select(User.id).where(User.id == user_id).with_for_update()).one()
        futures = [pool.submit(post, index, path, body) for index, (path, body) in enumerate(requests)]
        try:
            barrier.wait(timeout=10)
            deadline, waiting = time.monotonic() + 15, []
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as probe:
                while time.monotonic() < deadline:
                    # PostgreSQL truncates long User SELECT lists before their
                    # trailing FOR UPDATE; inspect the lock wait and query head.
                    waiting = list(probe.execute(sa.text("SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'SELECT users.%' ORDER BY pid")).scalars())
                    if queued_first is not None and waiting:
                        second_gate.set()
                    if len(waiting) >= len(requests):
                        break
                    if any(future.done() for future in futures):
                        break
                    time.sleep(.02)
            early = []
            for future in futures:
                if future.done():
                    try:
                        response = future.result()
                        early.append((response.status_code, response.text))
                    except Exception as error:
                        early.append((type(error).__name__, str(error)))
            activity = []
            if len(waiting) < len(requests):
                with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as probe:
                    activity = [dict(row) for row in probe.execute(sa.text("SELECT pid,state,wait_event_type,wait_event,length(query) AS query_length,right(query,160) AS query_tail FROM pg_stat_activity WHERE datname=current_database() ORDER BY pid")).mappings()]
            assert len(waiting) >= len(requests), f"Both commands must reach the shared User lock; early results: {early}; activity: {activity}"
            assert len(set(waiting)) == len(waiting)
        finally:
            second_gate.set()
            transaction.rollback()
        return [future.result(timeout=30) for future in futures], waiting


def _persisted(user_id):
    from app.database import SessionLocal
    from app.models import TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence, WorkoutSetLog, WorkoutLogCommand
    with SessionLocal() as db:
        sequences = db.query(TrainingSequence).filter_by(user_id=user_id).all()
        occurrences = db.query(WorkoutOccurrence).filter_by(user_id=user_id).order_by(WorkoutOccurrence.source_position).all()
        return {"sequence_count": len(sequences), "cursor": sequences[0].cursor,
            "contexts": [row.execution_context for row in occurrences], "states": [row.execution_state for row in occurrences],
            "advancement": occurrences[0].advancement, "occurrence_count": len(occurrences),
            "commands": [row.operation for row in db.query(TrainingSequenceCommand).filter_by(user_id=user_id).all()],
            "log_count": db.query(WorkoutSetLog).filter_by(user_id=user_id).count(),
            "log_command_count": db.query(WorkoutLogCommand).filter_by(user_id=user_id).count()}


def test_competing_enrollments_create_one_current_sequence(verified_target, account):
    user_id, headers, client = account
    request = _enrollment_request(client, headers)
    replies, pids = _race(verified_target, user_id, headers, [("/training/enroll", request),
        ("/training/enroll", {**request, "command_id": str(uuid4())})])
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
    persisted = _persisted(user_id)
    assert persisted["sequence_count"] == 1 and persisted["occurrence_count"] == 3
    assert persisted["commands"] == ["enroll"] and persisted["contexts"] == [None, None, None]
    _record("competing_enrollment", pids, replies)


def test_identical_enrollment_retries_return_one_receipt(verified_target, account):
    user_id, headers, client = account
    request = _enrollment_request(client, headers)
    replies, pids = _race(verified_target, user_id, headers, [("/training/enroll", request)] * 2)
    assert [reply.status_code for reply in replies] == [200, 200], [reply.text for reply in replies]
    assert replies[0].json() == replies[1].json()
    persisted = _persisted(user_id)
    assert persisted["sequence_count"] == 1 and persisted["occurrence_count"] == 3 and persisted["commands"] == ["enroll"]
    _record("identical_enrollment", pids, replies)


@pytest.mark.parametrize("same_command", [True, False])
def test_concurrent_start_binds_one_execution_context(verified_target, account, same_command):
    user_id, headers, client = account
    state = _enroll(client, headers)
    path, first = f'/training/{state["sequence_id"]}/start', _command(state)
    second = first if same_command else {**first, "command_id": str(uuid4())}
    replies, pids = _race(verified_target, user_id, headers, [(path, first), (path, second)])
    assert sorted(reply.status_code for reply in replies) == ([200, 200] if same_command else [200, 409]), [reply.text for reply in replies]
    winner = next(reply.json() for reply in replies if reply.status_code == 200)
    if same_command:
        assert replies[0].json() == replies[1].json()
    persisted = _persisted(user_id)
    assert persisted["contexts"] == [winner["execution_context"], None, None]
    assert persisted["states"] == ["active", "planned", "planned"] and persisted["cursor"] == 0
    assert sorted(persisted["commands"]) == ["enroll", "start"] and persisted["log_count"] == 0
    _record(f"start_same_command_{same_command}", pids, replies)


def _log_request(state):
    exercise = state["session"]["exercises"][0]
    return {"command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "set_index": 1,
        "reps": 8, "weight": 20, "set_kind": "work",
        "execution_context_id": (state.get("execution_context") or {}).get("id")}


def test_start_racing_unconfirmed_performance_cannot_implicitly_start_logging(verified_target, account):
    user_id, headers, client = account
    state = _enroll(client, headers)
    replies, pids = _race(verified_target, user_id, headers,
        [(f'/training/{state["sequence_id"]}/start', _command(state)),
         (f'/workout/{state["occurrence_id"]}/log-set', _log_request(state))])
    assert [reply.status_code for reply in replies] == [200, 409], [reply.text for reply in replies]
    persisted = _persisted(user_id)
    assert persisted["contexts"] == [replies[0].json()["execution_context"], None, None]
    assert persisted["log_count"] == persisted["log_command_count"] == 0
    _record("start_vs_unconfirmed_log", pids, replies)


@pytest.mark.parametrize("queued_first", [0, 1])
def test_end_early_racing_performance_preserves_the_serial_winner_and_replay(verified_target, account, queued_first):
    user_id, headers, client = account
    state = _enroll(client, headers)
    started = client.post(f'/training/{state["sequence_id"]}/start', headers=headers, json=_command(state))
    assert started.status_code == 200, started.text
    active = started.json()
    assert active["session"]["exercises"][0]["sets"] > 1
    end_path = f'/training/{state["sequence_id"]}/end-early'
    log_path = f'/workout/{state["occurrence_id"]}/log-set'
    end_request, log_request = _command(active, reason="Synthetic interruption"), _log_request(active)
    replies, pids = _race(verified_target, user_id, headers, [(end_path, end_request), (log_path, log_request)], queued_first=queued_first)
    assert [reply.status_code for reply in replies] == ([200, 409] if queued_first == 0 else [409, 200]), [reply.text for reply in replies]
    persisted = _persisted(user_id)
    if replies[1].status_code == 200:
        assert persisted["log_count"] == persisted["log_command_count"] == 1 and persisted["cursor"] == 0
        assert persisted["states"][0] == "active" and persisted["contexts"][0] == active["execution_context"]
        assert client.post(log_path, headers=headers, json=log_request).json() == replies[1].json()
        fresh = client.get("/training/next", headers=headers).json()
        ended = client.post(end_path, headers=headers, json=_command(fresh, reason="Confirmed after recorded set"))
        assert ended.status_code == 200, ended.text
        final = _persisted(user_id)
        assert final["cursor"] == 1 and final["log_count"] == final["log_command_count"] == 1
        assert final["advancement"]["coverage"]["completed"] == 1
    else:
        assert persisted["log_count"] == persisted["log_command_count"] == 0 and persisted["cursor"] == 1
        assert persisted["states"][0] == "ended_early" and persisted["contexts"] == [None, None, None]
        assert persisted["advancement"]["coverage"]["completed"] == 0
        assert client.post(end_path, headers=headers, json=end_request).json() == replies[0].json()
    _record(f"end_early_vs_log_first_{queued_first}", pids, replies)


@pytest.mark.parametrize("queued_first", [0, 1])
def test_enrollment_racing_calendar_activation_keeps_one_current_policy_owner(verified_target, account, queued_first):
    from app.database import SessionLocal
    from app.models import User, TrainingSequence, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog
    user_id, headers, client = account
    enrollment = _enrollment_request(client, headers)
    context = client.get("/plan/scheduling-context", headers=headers, params={"timezone": "America/New_York"})
    assert context.status_code == 200, context.text
    week = date.fromisoformat(context.json()["week_start"])
    calendar = {"template_id": "pure_bodybuilding_phase_1_full_body", "target_days": 3,
        "week_start": str(week), "timezone": "America/New_York", "expected_placement_revision": 0,
        "selected_dates": [str(week + timedelta(days=offset)) for offset in (1, 4, 6)]}
    preview = client.post("/plan/selected-dates/preview", headers=headers, json=calendar)
    assert preview.status_code == 200, preview.text
    calendar["expected_preview_digest"] = preview.json()["schedule"]["preview_digest"]
    replies, pids = _race(verified_target, user_id, headers,
        [("/training/enroll", enrollment), ("/plan/generate-week", calendar)], queued_first=queued_first)
    assert [reply.status_code for reply in replies] == ([200, 409] if queued_first == 0 else [409, 200]), [reply.text for reply in replies]
    with SessionLocal() as db:
        current = db.query(TrainingSequence).filter(TrainingSequence.user_id == user_id,
            TrainingSequence.state.in_(["active", "attention_required"])).all()
        plans = db.query(WorkoutPlan).filter_by(user_id=user_id).all()
        active_plans = [plan for plan in plans if (plan.payload.get("schedule") or {}).get("mode") == "selected_dates_v1"]
        assert len(current) + len(active_plans) == 1
        user = db.get(User, user_id)
        if queued_first == 0:
            assert len(current) == 1 and not plans
            assert user.schedule_mode == "flexible" and user.days_available is None
            assert db.query(WorkoutOccurrence).filter_by(user_id=user_id, sequence_id=current[0].id).count() == 3
        else:
            assert not current and len(active_plans) == 1
            assert user.schedule_mode == "calendar" and user.days_available == 3
            assert active_plans[0].payload["schedule"]["selected_dates"] == calendar["selected_dates"]
            assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 0
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 0
    _record(f"enrollment_vs_calendar_first_{queued_first}", pids, replies)
