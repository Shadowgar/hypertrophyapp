"""Effective logger coverage and immutable Flexible advancement/amendments."""
from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import uuid4

from test_flexible_lifecycle import scenario, small_source, enrollment, operation, next_state, clock
from app.database import SessionLocal
from app.models import TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence, WorkoutSetLog


def _prepare(scenario, monkeypatch):
    small_source(monkeypatch)
    clock(monkeypatch, datetime(2026, 10, 31, 23, 30, tzinfo=UTC))
    user_id, headers, client = scenario
    state, _ = enrollment(client, headers)
    return user_id, headers, client, state


def _operate(client, headers, state, name, **changes):
    response, payload = operation(client, headers, state, name, **changes)
    assert response.status_code == 200, response.text
    return response.json(), payload


def _required(state):
    return [(exercise, row["set_index"]) for exercise in state["session"]["exercises"]
        for row in exercise["authored_prescription"]["sets"]]


def _log(client, headers, state, exercise, index, **changes):
    payload = {"command_id": str(uuid4()), "exercise_id": exercise["id"],
        "primary_exercise_id": exercise.get("primary_exercise_id") or exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "set_index": index,
        "reps": 8, "weight": 20, "set_kind": "work",
        "execution_context_id": state["execution_context"]["id"], **changes}
    response = client.post(f'/workout/{state["occurrence_id"]}/log-set', headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def _log_all(client, headers, state, *, exclude=()):
    return [_log(client, headers, state, exercise, index) for exercise, index in _required(state)
        if (exercise["exercise_occurrence_id"], index) not in exclude]


def _snapshot(identity):
    with SessionLocal() as db:
        row = db.get(WorkoutOccurrence, identity)
        return {"id": row.id, "sequence_id": row.sequence_id, "payload": deepcopy(row.payload),
            "state": row.execution_state, "context": deepcopy(row.execution_context), "advancement": deepcopy(row.advancement)}


def _history_occurrence(client, headers, identity, day="2026-10-31"):
    response = client.get(f"/history/day/{day}", headers=headers)
    assert response.status_code == 200, response.text
    return next(workout for workout in response.json()["workouts"] if workout["workout_occurrence_id"] == identity)


def _correct(client, headers, receipt):
    payload = {"command_id": str(uuid4()), "reps": 9, "weight": 21, "reason": "Synthetic entered-value correction"}
    response = client.post(f'/workout/set/{receipt["id"]}/correct', headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def _undo(client, headers, state):
    exercise = state["session"]["exercises"][0]
    payload = {"command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "reason": "Synthetic historical undo"}
    response = client.post(f'/workout/{state["occurrence_id"]}/undo-last-set', headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def test_actual_required_sets_offer_explicit_finish_before_advancing(scenario, monkeypatch):
    user_id, headers, client, enrolled = _prepare(scenario, monkeypatch)
    active, _ = _operate(client, headers, enrolled, "start")
    original = _snapshot(active["occurrence_id"])
    receipts = _log_all(client, headers, active)
    ready = next_state(client, headers)
    assert ready["action"] == "finish" and ready["source_position"] == 0
    assert ready["coverage"]["complete"] and ready["coverage"]["completed"] == len(_required(active))
    assert _snapshot(active["occurrence_id"])["advancement"] is None
    advanced, finish_command = _operate(client, headers, ready, "finish")
    assert advanced["action"] == "start" and advanced["source_position"] == 1
    assert advanced["occurrence_id"] != active["occurrence_id"]
    frozen = _snapshot(active["occurrence_id"])
    assert frozen["state"] == "finished" and frozen["payload"] == original["payload"]
    assert frozen["advancement"]["coverage"]["complete"] and frozen["advancement"]["missing"] == []
    assert client.post(f'/training/{enrolled["sequence_id"]}/finish', headers=headers, json=finish_command).json() == advanced
    history = _history_occurrence(client, headers, active["occurrence_id"])
    assert history["status"] == "complete" and history["advancement"] == frozen["advancement"]
    with SessionLocal() as db:
        assert db.get(TrainingSequence, enrolled["sequence_id"]).cursor == 1
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 3
        assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == len(receipts)


def test_partial_actual_work_end_early_retains_exact_missing_work(scenario, monkeypatch):
    _, headers, client, enrolled = _prepare(scenario, monkeypatch)
    active, _ = _operate(client, headers, enrolled, "start")
    required = _required(active)
    assert len(required) > 1
    _log(client, headers, active, *required[0])
    partial = next_state(client, headers)
    denied, _ = operation(client, headers, partial, "finish")
    assert denied.status_code == 409
    assert next_state(client, headers)["source_position"] == 0
    ended, _ = _operate(client, headers, partial, "end-early", reason="Interrupted after actual work")
    advancement = ended["command_receipt"]["advancement"]
    assert advancement["operation"] == "end-early" and not advancement["coverage"]["complete"]
    assert advancement["coverage"]["completed"] == 1
    assert {(item["exercise_occurrence_id"], item["set_index"]) for item in advancement["missing"]} == {
        (exercise["exercise_occurrence_id"], index) for exercise, index in required[1:]}
    history = _history_occurrence(client, headers, active["occurrence_id"])
    assert history["status"] == "ended_early" and history["coverage_status"] == "incomplete"
    assert history["working_sets_completed"] == 1 and history["advancement"] == advancement
    assert ended["source_position"] == 1


def test_pause_resume_across_local_days_keeps_each_actual_set_date(scenario, monkeypatch):
    user_id, headers, client, enrolled = _prepare(scenario, monkeypatch)
    active, _ = _operate(client, headers, enrolled, "start")
    original = _snapshot(active["occurrence_id"])
    first_exercise, first_index = _required(active)[0]
    first, first_command = _log(client, headers, active, first_exercise, first_index)
    assert first["performed_local_date"] == "2026-10-31"
    paused, _ = _operate(client, headers, next_state(client, headers), "pause")
    assert paused["execution_context"] is None
    clock(monkeypatch, datetime(2026, 11, 2, 16, tzinfo=UTC))
    path = f'/workout/{active["occurrence_id"]}/log-set'
    assert client.post(path, headers=headers, json=first_command).json() == first
    stale = {**first_command, "command_id": str(uuid4()), "set_index": first_index + 1}
    assert client.post(path, headers=headers, json=stale).status_code == 409
    resumed, _ = _operate(client, headers, next_state(client, headers), "resume")
    assert resumed["occurrence_id"] == active["occurrence_id"]
    assert resumed["execution_context"]["id"] != active["execution_context"]["id"]
    assert resumed["execution_context"]["local_day"] == "2026-11-02"
    later = _log_all(client, headers, resumed, exclude={(first_exercise["exercise_occurrence_id"], first_index)})
    assert later and all(receipt["performed_local_date"] == "2026-11-02" for receipt, _ in later)
    _operate(client, headers, next_state(client, headers), "finish")
    frozen = _snapshot(active["occurrence_id"])
    assert frozen["payload"] == original["payload"]
    for day, expected_count in (("2026-10-31", 1), ("2026-11-02", len(later))):
        history = _history_occurrence(client, headers, active["occurrence_id"], day)
        assert history["total_sets"] == expected_count
        assert history["working_sets_completed"] == len(_required(active))
        assert history["actual_dates"] == ["2026-10-31", "2026-11-02"]
        assert all(row["performed_date"] == day for exercise in history["exercises"] for row in exercise["sets"])
    with SessionLocal() as db:
        rows = db.query(WorkoutSetLog).filter_by(user_id=user_id).all()
        assert {row.performed_local_date for row in rows} == {date(2026, 10, 31), date(2026, 11, 2)}
        assert {row.performed_timezone for row in rows} == {"America/New_York"}
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 3


def test_amendments_after_successor_start_preserve_advancement_and_allow_training(scenario, monkeypatch):
    _, headers, client, enrolled = _prepare(scenario, monkeypatch)
    first, _ = _operate(client, headers, enrolled, "start")
    receipts = _log_all(client, headers, first)
    successor, finish_command = _operate(client, headers, next_state(client, headers), "finish")
    finish_receipt = deepcopy(successor)
    as_of = _snapshot(first["occurrence_id"])
    successor, _ = _operate(client, headers, successor, "start")
    corrected, _ = _correct(client, headers, receipts[0][0])
    assert _history_occurrence(client, headers, first["occurrence_id"])["status"] == "complete"
    before_undo = next_state(client, headers)
    assert before_undo["action"] == "active" and before_undo["occurrence_id"] == successor["occurrence_id"]
    undone, undo_command = _undo(client, headers, first)
    assert undone["status"] == "ok"
    current = next_state(client, headers)
    assert current["sequence_id"] == enrolled["sequence_id"] and current["source_position"] == 1
    assert current["action"] == "active" and current["execution_context"] == successor["execution_context"]
    amended = _history_occurrence(client, headers, first["occurrence_id"])
    assert amended["status"] == "amended_incomplete" and amended["coverage_status"] == "incomplete"
    assert amended["advancement"] == as_of["advancement"]
    assert amended["missing"] == [[receipts[-1][0]["exercise_occurrence_id"], receipts[-1][0]["set_index"]]]
    assert _snapshot(first["occurrence_id"])["payload"] == as_of["payload"]
    assert _snapshot(first["occurrence_id"])["advancement"] == as_of["advancement"]
    assert client.post(f'/workout/{first["occurrence_id"]}/undo-last-set', headers=headers, json=undo_command).json() == undone
    assert client.post(f'/training/{enrolled["sequence_id"]}/finish', headers=headers, json=finish_command).json() == finish_receipt
    _log(client, headers, current, *_required(current)[0])
    with SessionLocal() as db:
        replacement = db.get(WorkoutSetLog, corrected["effective_set_id"])
        original = db.get(WorkoutSetLog, receipts[0][0]["id"])
        assert replacement.supersedes_id == original.id and original.voided_at is not None
        assert replacement.performed_local_date == original.performed_local_date == date(2026, 10, 31)
        assert replacement.execution_context_id == original.execution_context_id


def test_amending_finished_enrollment_a_never_reactivates_or_freezes_current_b(scenario, monkeypatch):
    user_id, headers, client, state = _prepare(scenario, monkeypatch)
    first = first_receipts = as_of = None
    sequence_a = state["sequence_id"]
    for position in range(3):
        active, _ = _operate(client, headers, state, "start")
        receipts = _log_all(client, headers, active)
        state, _ = _operate(client, headers, next_state(client, headers), "finish")
        if position == 0:
            first, first_receipts, as_of = active, receipts, _snapshot(active["occurrence_id"])
    assert state["state"] == "finished" and state["source_position"] == 3
    assert first is not None and first_receipts and as_of is not None
    new, _ = enrollment(client, headers)
    assert new["sequence_id"] != sequence_a
    current_b, _ = _operate(client, headers, new, "start")
    _correct(client, headers, first_receipts[0][0])
    _undo(client, headers, first)
    current = next_state(client, headers)
    assert current["sequence_id"] == new["sequence_id"] and current["state"] == "active"
    assert current["source_position"] == 0 and current["action"] == "active"
    assert current["execution_context"] == current_b["execution_context"]
    assert _history_occurrence(client, headers, first["occurrence_id"])["status"] == "amended_incomplete"
    assert _snapshot(first["occurrence_id"])["advancement"] == as_of["advancement"]
    assert _snapshot(first["occurrence_id"])["payload"] == as_of["payload"]
    _log(client, headers, current, *_required(current)[0])
    with SessionLocal() as db:
        old = db.get(TrainingSequence, sequence_a)
        assert old.state == "finished" and old.cursor == 3
        current_rows = db.query(TrainingSequence).filter(TrainingSequence.user_id == user_id,
            TrainingSequence.state.in_(["active", "attention_required"])).all()
        assert [row.id for row in current_rows] == [new["sequence_id"]]
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 6
        assert db.query(TrainingSequenceCommand).filter_by(user_id=user_id, operation="amendment_gate").count() == 0
