"""Negative lifecycle cases on the explicitly disposable scenario database."""
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

import pytest

from test_selected_date_scheduling import scenario
from test_flexible_lifecycle import small_source, enrollment, operation, next_state
from auth_test_helpers import create_access_token
from app import flexible_training as training
from app.database import SessionLocal
from app.models import User, TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence, WorkoutSetLog


@pytest.mark.parametrize("stale", ["day", "digest", "revision"])
def test_stale_start_does_not_create_execution_authority(scenario, monkeypatch, stale):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    changes = {
        "day": {"expected_local_day": str(date.fromisoformat(state["local_day"]) - timedelta(days=1))},
        "digest": {"expected_digest": "0" * 64},
        "revision": {"expected_revision": state["revision"] + 1},
    }[stale]
    response, _ = operation(client, headers, state, "start", **changes)
    assert response.status_code == 409, response.text
    assert next_state(client, headers) == state
    with SessionLocal() as db:
        occurrence = db.get(WorkoutOccurrence, state["occurrence_id"])
        assert occurrence.execution_state == "planned"
        assert occurrence.execution_context is None
        assert db.query(TrainingSequenceCommand).filter_by(user_id=uid, operation="start").count() == 0


def test_other_account_cannot_command_or_replay_owned_sequence(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    accepted, request = operation(client, headers, state, "start")
    assert accepted.status_code == 200, accepted.text
    foreign_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=foreign_id, email=f"{uuid4()}@example.com", name="Synthetic other account",
            password_hash="unused", selected_program_id="pure_bodybuilding_phase_1_full_body"))
        db.commit()
    foreign = {"Authorization": f"Bearer {create_access_token(foreign_id)}"}
    response = client.post(f'/training/{state["sequence_id"]}/start', headers=foreign, json=request)
    assert response.status_code == 404, response.text
    assert client.get('/training/next', headers=foreign).json() == {"mode": "calendar", "action": "none"}
    with SessionLocal() as db:
        assert db.query(TrainingSequenceCommand).filter_by(user_id=foreign_id).count() == 0
        assert db.query(TrainingSequence).filter_by(user_id=uid).one().cursor == 0


def test_second_stale_start_cannot_replace_first_execution_context(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    first, request = operation(client, headers, state, "start")
    assert first.status_code == 200, first.text
    second, _ = operation(client, headers, state, "start")
    assert second.status_code == 409, second.text
    current = next_state(client, headers)
    assert current["execution_context"] == first.json()["execution_context"]
    assert current["revision"] == first.json()["revision"]
    assert client.post(f'/training/{state["sequence_id"]}/start', headers=headers, json=request).json() == first.json()
    with SessionLocal() as db:
        assert db.query(TrainingSequenceCommand).filter_by(user_id=uid, operation="start").count() == 1


def test_same_command_identifier_cannot_bind_different_payload(scenario, monkeypatch):
    small_source(monkeypatch)
    _, headers, client = scenario
    state, _ = enrollment(client, headers)
    response, request = operation(client, headers, state, "start")
    assert response.status_code == 200, response.text
    changed = client.post(f'/training/{state["sequence_id"]}/start', headers=headers,
        json={**request, "reason": "Different request under the accepted identifier"})
    assert changed.status_code == 409, changed.text
    assert next_state(client, headers)["execution_context"] == response.json()["execution_context"]


def test_missing_intermediate_source_item_blocks_and_can_retire_without_fake_exhaustion(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    started, _ = operation(client, headers, state, "start")
    assert started.status_code == 200, started.text
    with SessionLocal() as db:
        missing = db.query(WorkoutOccurrence).filter_by(user_id=uid,
            sequence_id=state["sequence_id"], source_position=1).one()
        db.delete(missing)
        db.commit()
    blocked = next_state(client, headers)
    assert blocked["action"] == "blocked"
    assert any(item["code"] == "source_admission_conflict" for item in blocked["blockers"])
    denied, _ = operation(client, headers, blocked, "end-early", reason="Must not skip a missing source item")
    assert denied.status_code == 409, denied.text
    with SessionLocal() as db:
        sequence = db.get(TrainingSequence, state["sequence_id"])
        assert sequence.cursor == 0
        assert sequence.state != "finished"
        assert db.get(WorkoutOccurrence, state["occurrence_id"]).advancement is None
    retired, _ = operation(client, headers, next_state(client, headers), "retire", reason="Source reconciliation required")
    assert retired.status_code == 200, retired.text
    assert retired.json()["state"] == "retired"


def _receipt(db, *, user_id, occurrence, exercise, day):
    db.add(WorkoutSetLog(id=str(uuid4()), user_id=user_id, workout_id=occurrence.workout_id,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        primary_exercise_id=exercise["primary_exercise_id"], exercise_id=exercise["id"],
        set_index=1, reps=8, weight=20, set_kind="work", performed_local_date=day,
        performed_timezone="America/New_York", execution_context_id=str(uuid4())))


@pytest.mark.parametrize("closure", ["finish", "end-early"])
def test_changed_frozen_prescription_cannot_advance_even_with_reviewed_digest(scenario, monkeypatch, closure):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    started, _ = operation(client, headers, state, "start")
    assert started.status_code == 200, started.text
    with SessionLocal() as db:
        occurrence = db.get(WorkoutOccurrence, state["occurrence_id"])
        payload = deepcopy(occurrence.payload)
        exercise = payload["exercises"][0]
        exercise["authored_prescription"]["raw"]["rest"] = "unreviewed changed prescription"
        if closure == "finish":
            exercise["sets"] = 1
            exercise["authored_prescription"]["sets"] = exercise["authored_prescription"]["sets"][:1]
            _receipt(db, user_id=uid, occurrence=occurrence, exercise=exercise,
                day=date.fromisoformat(state["local_day"]))
        occurrence.payload = payload
        db.commit()
    blocked = next_state(client, headers)
    assert blocked["action"] == "blocked"
    assert any(item["code"] == "source_admission_conflict" for item in blocked["blockers"])
    assert blocked["coverage"]["complete"] is (closure == "finish")
    response, _ = operation(client, headers, blocked, closure, reason="Review cannot authorize a changed prescription")
    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        assert db.get(TrainingSequence, state["sequence_id"]).cursor == 0
        assert db.get(WorkoutOccurrence, state["occurrence_id"]).advancement is None


def test_old_enrollment_cannot_supply_current_mandatory_antecedent_evidence(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    day = date.fromisoformat(state["local_day"])
    with SessionLocal() as db:
        current = db.get(TrainingSequence, state["sequence_id"])
        occurrence = db.get(WorkoutOccurrence, state["occurrence_id"])
        old_sequence = TrainingSequence(id=str(uuid4()), user_id=uid, program_id=current.program_id,
            source_digest=current.source_digest, source_catalog=deepcopy(current.source_catalog),
            timezone=current.timezone, revision=1, cursor=0, state="retired", consent={"confirmed": True})
        db.add(old_sequence)
        db.flush()
        old_id = str(uuid4())
        old_payload = deepcopy(occurrence.payload)
        old_payload["workout_occurrence_id"] = old_id
        old_payload["exercises"][0]["exercise_occurrence_id"] = str(uuid4())
        old = WorkoutOccurrence(id=old_id, user_id=uid, sequence_id=old_sequence.id,
            source_position=0, source_week=1, source_session=1, plan_id=None, week_start=None,
            session_slot=0, workout_id=occurrence.workout_id, program_id=current.program_id,
            payload=old_payload, prescription_digest=occurrence.prescription_digest, execution_state="ended_early")
        db.add(old)
        db.flush()
        _receipt(db, user_id=uid, occurrence=old, exercise=old_payload["exercises"][0], day=day - timedelta(days=7))
        db.commit()
        assert training._actual_days(db, current) == {}
        exercise = occurrence.payload["exercises"][0]
        _receipt(db, user_id=uid, occurrence=occurrence, exercise=exercise, day=day)
        db.commit()
        slot = exercise["source_lineage"]["source_slot_id"]
        assert training._actual_days(db, current) == {slot: [day]}
