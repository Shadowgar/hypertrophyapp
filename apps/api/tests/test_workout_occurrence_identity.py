"""Synthetic, explicitly isolated targets only. Also run against migrated PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutPlan, WorkoutSetLog, WorkoutSessionState, WorkoutLogCommand, WorkoutOccurrence, ExerciseState
from app.security import create_access_token
from app.workout_identity import identified_sessions


@pytest.fixture
def scenario():
    # No default DB fallback is allowed for this suite.
    explicit = os.environ.get("TEST_DATABASE_URL")
    assert explicit == engine.url.render_as_string(hide_password=False), "Explicit synthetic database required"
    if engine.dialect.name == "sqlite":
        assert Path(engine.url.database).resolve().is_relative_to(Path(os.environ.get("HIST_TEST_ROOT") or os.environ["RUNNER_TEMP"]))
        Base.metadata.create_all(engine)
    else:
        assert engine.url.database.startswith("hist_disposable")
        assert os.environ.get("HIST_MIGRATED_DATABASE") == "1"
    with SessionLocal() as db:
        user = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid", name="Synthetic history", password_hash="unused", selected_program_id="full_body_v1")
        db.add(user)
        db.commit()
        user_id = user.id
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}
    return user_id, headers, TestClient(app)


def plan(user_id, week, *, repeats=False, program="full_body_v1"):
    exercise = {"id": "same-catalog", "primary_exercise_id": "same-catalog", "name": "Synthetic exercise", "sets": 3,
                "rep_range": [8, 12], "recommended_working_weight": 25, "movement_pattern": "squat"}
    with SessionLocal() as db:
        row = WorkoutPlan(user_id=user_id, week_start=week, split="full_body", phase="maintenance",
            created_at=datetime.combine(week, datetime.min.time()), payload={"program_template_id": program, "sessions": [
                {"session_id": "reused-template", "title": "Synthetic", "date": week.isoformat(), "exercises": [exercise, deepcopy(exercise)] if repeats else [exercise]}]})
        db.add(row)
        db.commit()
        return identified_sessions(row)[0]


def submission(session, *, slot=0, command=None, index=1):
    exercise = session["exercises"][slot]
    return {"command_id": command or str(uuid4()), "exercise_occurrence_id": exercise["exercise_occurrence_id"],
            "exercise_id": exercise["id"], "set_index": index, "reps": 10, "weight": 25}


def log(client, headers, session, payload):
    return client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers, json=payload)


def counts(user_id):
    with SessionLocal() as db:
        return (db.query(WorkoutSetLog).filter_by(user_id=user_id).count(),
                db.query(WorkoutSessionState).filter_by(user_id=user_id).count(),
                db.query(WorkoutLogCommand).filter_by(user_id=user_id).count())


@pytest.mark.parametrize("program", ["full_body_v1", "pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"])
def test_week_isolation_today_resume_progress_and_undo(scenario, program):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7), program=program)
    payload = submission(first)
    original = log(client, headers, first, payload)
    assert original.status_code == 200, original.text
    second = plan(user, date(2026, 9, 14), program=program)
    assert first["workout_occurrence_id"] != second["workout_occurrence_id"]
    today = client.get("/workout/today", headers=headers).json()
    assert today["workout_occurrence_id"] == second["workout_occurrence_id"]
    assert today["resume"] is False
    assert today["exercises"][0]["completed_sets"] == 0
    assert client.get(f"/workout/{second['workout_occurrence_id']}/progress", headers=headers).json()["completed_total"] == 0
    assert log(client, headers, second, submission(second)).status_code == 200
    assert client.post(f"/workout/{second['workout_occurrence_id']}/undo-last-set", headers=headers,
        json={"exercise_id": "same-catalog", "exercise_occurrence_id": second["exercises"][0]["exercise_occurrence_id"]}).status_code == 200
    assert client.get(f"/workout/{first['workout_occurrence_id']}/progress", headers=headers).json()["completed_total"] == 1
    assert counts(user) == (1, 2, 2)
    # Returning to a previous explicit occurrence retains its original result.
    assert log(client, headers, first, payload).json() == original.json()


def test_repeated_workout_template_slots_have_distinct_identity(scenario):
    user, headers, client = scenario
    plan(user, date(2026, 9, 7))
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user).one()
        payload = deepcopy(row.payload)
        payload["sessions"].append(deepcopy(payload["sessions"][0]))
        payload["sessions"][1]["exercises"][0]["sets"] = 5
        row.payload = payload
        db.commit()
        first, second = identified_sessions(row)
    assert first["workout_occurrence_id"] != second["workout_occurrence_id"]
    assert log(client, headers, first, submission(first)).status_code == 200
    progress = client.get(f"/workout/{second['workout_occurrence_id']}/progress", headers=headers)
    assert progress.status_code == 200
    assert progress.json()["completed_total"] == 0
    assert client.get("/workout/reused-template/progress", headers=headers).status_code == 409
    for index in (2, 3):
        assert log(client, headers, first, submission(first, index=index)).status_code == 200
    today = client.get("/workout/today", headers=headers).json()
    assert today["workout_occurrence_id"] == second["workout_occurrence_id"]
    assert today["total_sets"] == today["planned_total"] == 5
    assert today["exercises"][0]["completed_sets"] == 0


def test_repeated_catalog_slots_are_separate(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7), repeats=True)
    assert session["exercises"][0]["exercise_occurrence_id"] != session["exercises"][1]["exercise_occurrence_id"]
    for slot in (0, 1):
        assert log(client, headers, session, submission(session, slot=slot)).status_code == 200
    assert counts(user) == (2, 2, 2)
    progress = client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers).json()
    assert [row["completed_sets"] for row in progress["exercises"]] == [1, 1]
    summary = client.get(f"/workout/{session['workout_occurrence_id']}/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert [row["performed_sets"] for row in summary.json()["exercises"]] == [1, 1]
    today = client.get("/workout/today", headers=headers).json()
    assert [row["completed_sets"] for row in today["exercises"]] == [1, 1]
    assert today["resume"] is True
    assert client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers,
        json={"exercise_id": "same-catalog", "exercise_occurrence_id": session["exercises"][1]["exercise_occurrence_id"]}).status_code == 200
    progress = client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers).json()
    assert [row["completed_sets"] for row in progress["exercises"]] == [1, 0]
    ambiguous = submission(session)
    ambiguous.pop("exercise_occurrence_id")
    assert log(client, headers, session, ambiguous).status_code == 409


def test_retry_original_result_and_no_resurrection_after_undo(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    payload = submission(session)
    first = log(client, headers, session, payload)
    assert first.status_code == 200, first.text
    assert log(client, headers, session, {**payload, "weight": 25.0, "set_kind": "WORK"}).json() == first.json()
    assert log(client, headers, session, submission(session, index=2)).status_code == 200
    assert log(client, headers, session, payload).json() == first.json()
    assert counts(user) == (2, 1, 2)
    for _ in range(2):
        assert client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers,
            json={"exercise_id": "same-catalog", "exercise_occurrence_id": payload["exercise_occurrence_id"]}).status_code == 200
    assert log(client, headers, session, payload).json() == first.json()
    assert counts(user) == (0, 1, 2)


@pytest.mark.parametrize("field,value", [("reps", 9), ("weight", 30), ("exercise_id", "other"), ("exercise_occurrence_id", str(uuid4()))])
def test_changed_payload_conflicts_without_mutation(scenario, field, value):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    payload = submission(session)
    assert log(client, headers, session, payload).status_code == 200
    with SessionLocal() as db:
        state = db.query(ExerciseState).filter_by(user_id=user).one()
        before = (state.exposure_count, state.current_working_weight, state.fatigue_score)
    assert log(client, headers, session, {**payload, field: value}).status_code == 409
    second = plan(user, date(2026, 9, 14))
    assert log(client, headers, second, payload).status_code == 409
    assert counts(user) == (1, 1, 1)
    with SessionLocal() as db:
        state = db.query(ExerciseState).filter_by(user_id=user).one()
        assert (state.exposure_count, state.current_working_weight, state.fatigue_score) == before


def test_cross_user_command_isolation_and_foreign_occurrence_rejection(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    command = str(uuid4())
    assert log(client, headers, first, submission(first, command=command)).status_code == 200
    with SessionLocal() as db:
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid", name="Other", password_hash="unused", selected_program_id="full_body_v1")
        db.add(other); db.commit(); other_id = other.id
    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    assert log(client, other_headers, first, submission(first, command=command)).status_code == 404
    second = plan(other_id, date(2026, 9, 7))
    response = log(client, other_headers, second, submission(second, command=command))
    assert response.status_code == 200, response.text
    assert response.json()["workout_occurrence_id"] == second["workout_occurrence_id"]
    assert counts(user) == counts(other_id) == (1, 1, 1)


def test_legacy_history_preserved_and_excluded_from_occurrence_counts(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    with SessionLocal() as db:
        old = WorkoutSetLog(user_id=user, workout_id="reused-template", primary_exercise_id="same-catalog", exercise_id="same-catalog", set_index=3, reps=8, weight=20)
        old_state = WorkoutSessionState(user_id=user, workout_id="reused-template", primary_exercise_id="same-catalog", exercise_id="same-catalog", planned_sets=3,
            planned_reps_min=8, planned_reps_max=12, planned_weight=20, completed_sets=3, recommended_reps_min=8, recommended_reps_max=12,
            recommended_weight=20, last_guidance="legacy", set_history=[])
        db.add_all([old, old_state]); db.commit(); old_id = old.id; state_id = old_state.id
    assert client.get("/workout/today", headers=headers).json()["exercises"][0]["completed_sets"] == 0
    assert log(client, headers, session, submission(session)).status_code == 200
    with SessionLocal() as db:
        old = db.get(WorkoutSetLog, old_id); state = db.get(WorkoutSessionState, state_id)
        assert old.workout_occurrence_id is old.exercise_occurrence_id is old.command_id is None
        assert (old.reps, old.weight, old.set_index) == (8, 20, 3)
        assert state.workout_occurrence_id is state.exercise_occurrence_id is None
        assert state.completed_sets == 3


def test_started_snapshot_survives_plan_edit_and_removal(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    assert log(client, headers, session, submission(session)).status_code == 200
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user).one()
        changed = deepcopy(row.payload); changed["sessions"][0]["exercises"][0]["sets"] = 99
        row.payload = changed; db.commit()
    assert client.get("/workout/today", headers=headers).json()["exercises"][0]["sets"] == 3
    with SessionLocal() as db:
        db.delete(db.query(WorkoutPlan).filter_by(user_id=user).one()); db.commit()
    assert client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers).json()["planned_total"] == 3


def test_database_unique_command_constraint(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    payload = submission(session)
    assert log(client, headers, session, payload).status_code == 200
    with SessionLocal() as db:
        original = db.query(WorkoutLogCommand).filter_by(user_id=user).one()
        db.add(WorkoutLogCommand(user_id=user, command_id=original.command_id, request_digest=original.request_digest,
            workout_occurrence_id=original.workout_occurrence_id, exercise_occurrence_id=original.exercise_occurrence_id, response=original.response))
        with pytest.raises(IntegrityError): db.flush()
        db.rollback()


def test_regeneration_guard_uses_plan_occurrences(scenario):
    from app.routers.plan import _current_regenerate_would_replace_with_existing_progress
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    assert log(client, headers, first, submission(first)).status_code == 200
    second = plan(user, date(2026, 9, 14))
    with SessionLocal() as db:
        owner = db.get(User, user)
        def guarded(week):
            row = db.query(WorkoutPlan).filter_by(user_id=user, week_start=week).one()
            return _current_regenerate_would_replace_with_existing_progress(db=db, current_user=owner,
                plan_runtime={"record_values": {"week_start": week, "payload": row.payload}})
        assert guarded(date(2026, 9, 7)) is True
        assert guarded(date(2026, 9, 14)) is False
    assert log(client, headers, second, submission(second)).status_code == 200
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user, week_start=date(2026, 9, 14)).one()
        assert _current_regenerate_would_replace_with_existing_progress(db=db, current_user=db.get(User, user),
            plan_runtime={"record_values": {"week_start": row.week_start, "payload": row.payload}}) is True


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL transaction qualification")
@pytest.mark.parametrize("conflict", [False, True])
def test_postgres_concurrent_same_command(scenario, conflict):
    user, headers, _ = scenario
    session = plan(user, date(2026, 9, 7))
    payload = submission(session)
    barrier = Barrier(2)
    def submit(changed):
        with TestClient(app) as client:
            barrier.wait(timeout=10)
            return log(client, headers, session, {**payload, "reps": 9 if changed else 10})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit, False), pool.submit(submit, conflict)]
        results = [future.result(timeout=30) for future in futures]
    assert sorted(result.status_code for result in results) == ([200, 409] if conflict else [200, 200])
    if not conflict: assert results[0].json() == results[1].json()
    assert counts(user) == (1, 1, 1)
    with SessionLocal() as db:
        assert db.query(WorkoutSessionState).filter_by(user_id=user).one().completed_sets == 1


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL transaction qualification")
def test_postgres_concurrent_distinct_commands_preserve_projection(scenario):
    user, headers, _ = scenario
    session = plan(user, date(2026, 9, 7))
    barrier = Barrier(2)
    def submit(index):
        client = TestClient(app)
        barrier.wait(timeout=10)
        return log(client, headers, session, submission(session, index=index))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [1, 2]))
    assert [result.status_code for result in results] == [200, 200]
    assert counts(user) == (2, 1, 2)
    with SessionLocal() as db:
        assert db.query(WorkoutSessionState).filter_by(user_id=user).one().completed_sets == 2
