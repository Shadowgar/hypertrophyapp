"""Finite resolution of declared mandatory rest; synthetic source, real commands."""
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from test_selected_date_scheduling import scenario
from test_flexible_lifecycle import small_source, enrollment, operation, next_state, clock
from app.database import SessionLocal
from app.models import TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence, WorkoutSetLog


def mandatory_source(monkeypatch):
    source = small_source(monkeypatch)
    before = source["items"][0]["session"]["exercises"][0]
    after = source["items"][1]["session"]["exercises"][0]
    slots = [before["source_lineage"]["source_slot_id"], after["source_lineage"]["source_slot_id"]]
    relation = {"kind": "minimum_rest", "group_id": "synthetic-native-cross-week-rest",
        "source_slot_ids": slots, "minimum_rest_days": 2, "hard": True,
        "source_row": 1, "raw": "Synthetic fixture: two full rest days"}
    for exercise in (before, after):
        exercise["source_relationships"].append(deepcopy(relation))
    source["rest_rules"] = [{"kind": "minimum_rest", "group_id": relation["group_id"],
        "source_slot_ids": slots, "minimum_rest_days": 2, "source_positions": [0, 1]}]
    return source


def start_first(client, headers):
    state, _ = enrollment(client, headers)
    started, _ = operation(client, headers, state, "start")
    assert started.status_code == 200, started.text
    return started.json()


def test_known_rest_has_earliest_day_and_explicit_recheck_releases_work(scenario, monkeypatch):
    mandatory_source(monkeypatch)
    clock(monkeypatch, datetime(2026, 10, 30, 16, tzinfo=UTC))
    uid, headers, client = scenario
    active = start_first(client, headers)
    exercise = active["session"]["exercises"][0]
    logged = client.post(f'/workout/{active["occurrence_id"]}/log-set', headers=headers, json={
        "command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "set_index": 1,
        "reps": 8, "weight": 20, "set_kind": "work",
        "execution_context_id": active["execution_context"]["id"]})
    assert logged.status_code == 200, logged.text
    assert logged.json()["performed_local_date"] == "2026-10-30"
    ended, _ = operation(client, headers, next_state(client, headers), "end-early", reason="Preserve remaining work")
    assert ended.status_code == 200, ended.text
    blocked = ended.json()
    assert blocked["source_position"] == 1
    assert blocked["action"] == "blocked"
    rest = next(item for item in blocked["blockers"] if item["code"] == "hard_rest_wait")
    assert rest["earliest_day"] == "2026-11-02"
    assert "reconcile" in blocked["resolution_options"]
    denied, _ = operation(client, headers, blocked, "start")
    assert denied.status_code == 409, denied.text
    premature, _ = operation(client, headers, next_state(client, headers), "reconcile")
    assert premature.status_code == 409, premature.text
    with SessionLocal() as db:
        before_revision = db.get(TrainingSequence, blocked["sequence_id"]).revision
        advancement = deepcopy(db.get(WorkoutOccurrence, active["occurrence_id"]).advancement)
    clock(monkeypatch, datetime(2026, 11, 2, 16, tzinfo=UTC))
    stale, _ = operation(client, headers, blocked, "reconcile")
    assert stale.status_code == 409, stale.text
    fresh = next_state(client, headers)
    assert fresh["revision"] == before_revision
    # A routine wait is derived, so confirmed Start can itself recheck it.
    # Explicit Reconcile is also supported; reads never advance the cursor.
    assert fresh["action"] == "start" and fresh["blockers"] == []
    rechecked, request = operation(client, headers, fresh, "reconcile")
    assert rechecked.status_code == 200, rechecked.text
    released = rechecked.json()
    assert released["action"] == "start" and released["blockers"] == []
    assert released["source_position"] == 1
    assert client.post(f'/training/{released["sequence_id"]}/reconcile', headers=headers, json=request).json() == released
    started, _ = operation(client, headers, next_state(client, headers), "start")
    assert started.status_code == 200, started.text
    assert started.json()["occurrence_id"] == blocked["occurrence_id"]
    with SessionLocal() as db:
        assert db.get(WorkoutOccurrence, active["occurrence_id"]).advancement == advancement
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 1
        assert db.query(TrainingSequenceCommand).filter_by(user_id=uid, operation="reconcile").count() == 1


def test_unknown_mandatory_evidence_can_retire_without_completion_or_rule_bypass(scenario, monkeypatch):
    mandatory_source(monkeypatch)
    clock(monkeypatch, datetime(2026, 10, 30, 16, tzinfo=UTC))
    uid, headers, client = scenario
    active = start_first(client, headers)
    ended, _ = operation(client, headers, active, "end-early", reason="No work performed")
    assert ended.status_code == 200, ended.text
    blocked = ended.json()
    assert blocked["action"] == "blocked"
    assert blocked["source_position"] == 1
    assert any(item["code"] == "mandatory_evidence_unknown" for item in blocked["blockers"])
    assert "retire" in blocked["resolution_options"]
    for name in ("start", "reconcile", "end-early"):
        denied, _ = operation(client, headers, next_state(client, headers), name)
        assert denied.status_code == 409, denied.text
    unconfirmed, _ = operation(client, headers, next_state(client, headers), "retire", confirmed=False)
    assert unconfirmed.status_code == 409, unconfirmed.text
    retired, request = operation(client, headers, next_state(client, headers), "retire", reason="Missing mandatory source evidence")
    assert retired.status_code == 200, retired.text
    result = retired.json()
    assert result["state"] == "retired"
    assert result["source_position"] == 1
    assert any(item["code"] == "mandatory_evidence_unknown" for item in result["command_receipt"]["reconciliation"])
    clock(monkeypatch, datetime(2026, 11, 30, 16, tzinfo=UTC))
    assert client.post(f'/training/{result["sequence_id"]}/retire', headers=headers, json=request).json() == result
    with SessionLocal() as db:
        sequence = db.get(TrainingSequence, result["sequence_id"])
        assert sequence.state == "retired" and sequence.cursor == 1
        original = db.get(WorkoutOccurrence, active["occurrence_id"])
        assert original.execution_state == "ended_early"
        assert original.advancement["coverage"]["complete"] is False
        assert original.advancement["missing"]
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid, sequence_id=sequence.id).count() == 3
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0
    # Retirement is terminal ownership, not an ignore-rest grant for reenrollment.
    fresh_active = start_first(client, headers)
    ended_again, _ = operation(client, headers, fresh_active, "end-early", reason="Still no performed antecedent")
    assert ended_again.status_code == 200, ended_again.text
    assert ended_again.json()["sequence_id"] != result["sequence_id"]
    assert ended_again.json()["action"] == "blocked"
    assert any(item["code"] == "mandatory_evidence_unknown" for item in ended_again.json()["blockers"])


def test_historical_mandatory_attention_requires_explicit_reconciliation_after_wait(scenario, monkeypatch):
    mandatory_source(monkeypatch)
    clock(monkeypatch, datetime(2026, 10, 30, 16, tzinfo=UTC))
    uid, headers, client = scenario
    active = start_first(client, headers)
    exercise = active["session"]["exercises"][0]
    logged = client.post(f'/workout/{active["occurrence_id"]}/log-set', headers=headers, json={
        "command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "set_index": 1,
        "reps": 8, "weight": 20, "set_kind": "work",
        "execution_context_id": active["execution_context"]["id"]})
    assert logged.status_code == 200, logged.text
    ended, _ = operation(client, headers, next_state(client, headers), "end-early", reason="Interrupted")
    assert ended.status_code == 200, ended.text
    with SessionLocal() as db:
        original = db.query(WorkoutSetLog).filter_by(user_id=uid, workout_occurrence_id=active["occurrence_id"]).one()
        receipt_id = original.id
        advancement = deepcopy(db.get(WorkoutOccurrence, active["occurrence_id"]).advancement)
    corrected = client.post(f'/workout/set/{receipt_id}/correct', headers=headers, json={
        "command_id": str(uuid4()), "reps": 8, "weight": 21,
        "reason": "Correct performed load while the actual source-rest conflict remains"})
    assert corrected.status_code == 200, corrected.text
    gated = next_state(client, headers)
    assert gated["state"] == "attention_required" and gated["action"] == "blocked"
    assert any(item["code"] == "hard_rest_wait" for item in gated["blockers"])
    clock(monkeypatch, datetime(2026, 11, 2, 16, tzinfo=UTC))
    elapsed = next_state(client, headers)
    assert elapsed["blockers"] == []
    assert elapsed["state"] == "attention_required" and elapsed["action"] == "blocked"
    denied, _ = operation(client, headers, elapsed, "start")
    assert denied.status_code == 409, denied.text
    resolved, _ = operation(client, headers, next_state(client, headers), "reconcile")
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["state"] == "active" and resolved.json()["action"] == "start"
    started, _ = operation(client, headers, next_state(client, headers), "start")
    assert started.status_code == 200, started.text
    assert started.json()["source_position"] == 1
    with SessionLocal() as db:
        assert db.get(WorkoutOccurrence, active["occurrence_id"]).advancement == advancement
        assert db.get(WorkoutOccurrence, active["occurrence_id"]).execution_state == "ended_early"
        assert db.query(WorkoutSetLog).filter_by(user_id=uid, voided_at=None).count() == 1


def test_missing_frozen_exercise_identity_has_a_terminal_retirement_path(scenario, monkeypatch):
    mandatory_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    with SessionLocal() as db:
        occurrence = db.get(WorkoutOccurrence, state["occurrence_id"])
        payload = deepcopy(occurrence.payload)
        payload["exercises"][0].pop("exercise_occurrence_id")
        occurrence.payload = payload
        db.commit()
    blocked = next_state(client, headers)
    assert blocked["action"] == "blocked"
    assert blocked["coverage"]["known"] is False
    assert any(item["code"] == "source_admission_conflict" for item in blocked["blockers"])
    assert "retire" in blocked["resolution_options"]
    denied, _ = operation(client, headers, blocked, "start")
    assert denied.status_code == 409, denied.text
    retired, _ = operation(client, headers, next_state(client, headers), "retire", reason="Frozen execution identity cannot be admitted")
    assert retired.status_code == 200, retired.text
    assert retired.json()["state"] == "retired"
    assert retired.json()["source_position"] == 0
    with SessionLocal() as db:
        original = db.get(WorkoutOccurrence, state["occurrence_id"])
        assert original.payload == payload
        assert original.advancement is None
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0
