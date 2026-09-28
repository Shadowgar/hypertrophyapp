"""Synthetic compatibility and frozen-source evidence on explicitly disposable DBs."""
from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adaptive_schema import AuthoredTarget
from app.database import SessionLocal
from app.models import WorkoutPlan, WorkoutSetLog, WorkoutOccurrence, ExerciseState, WorkoutSessionState
from app.models import WorkoutLogCommand
from core_engine.authored_prescription import preserve_prescription, uniform_rep_range
from core_engine.decision_workout_session import resolve_workout_log_set_plan_context
from test_workout_occurrence_identity import scenario, plan, submission, log


def typed_plan(user_id, *, raw="AMRAP"):
    session = plan(user_id, date.today(), program="pure_bodybuilding_phase_2_full_body")
    exercise = session["exercises"][0]
    prescribed = preserve_prescription({"reps": raw, "working_sets": "2", "early_set_rpe": "~8-9", "last_set_rpe": "10", "rest": "~2-3 min"}, 2)
    lineage = {"source_program_id": "synthetic", "source_slot_id": "synthetic:w6:d5:s6", "source_week": 6,
        "source_session": 5, "source_slot": 6, "artifact_version": "0.3.0", "source_sha256": "0" * 64,
        "artifact_sha256": "1" * 64, "importer_version": "authored-fidelity-1"}
    for item in prescribed["sets"]:
        item["source_set_id"] = f"{lineage['source_slot_id']}:set{item['set_index']}"
    exercise.update(sets=2, rep_range=uniform_rep_range(prescribed), authored_prescription=prescribed, source_lineage=lineage)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session["plan_id"])
        row.payload = {**row.payload, "sessions": [{key: value for key, value in session.items() if key not in ("plan_id", "week_start", "session_slot", "workout_occurrence_id")}]}
        db.commit()
    return session


@pytest.mark.parametrize("raw", ["AMRAP", "6, 10", "3+", None])
def test_typed_receipts_retry_correction_undo_and_no_numeric_projection(scenario, raw):
    user, headers, client = scenario
    session = typed_plan(user, raw=raw)
    exercise = session["exercises"][0]
    before = deepcopy(exercise)
    payload = submission(session)
    result = log(client, headers, session, payload)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["planned_reps_min"] is None and data["planned_reps_max"] is None and data["rep_delta"] is None
    assert data["live_recommendation"]["recommended_reps_min"] is None
    assert data["decision_trace"]["numeric_progression"] == "not_applicable"
    assert log(client, headers, session, payload).json() == data
    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200
    assert today.json()["exercises"][0]["authored_prescription"] == before["authored_prescription"]
    assert today.json()["exercises"][0]["completed_sets"] == 1
    summary = client.get(f"/workout/{session['workout_occurrence_id']}/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["exercises"][0]["planned_reps_min"] is None
    assert summary.json()["exercises"][0]["average_performed_reps"] == payload["reps"]
    with SessionLocal() as db:
        assert db.query(ExerciseState).filter_by(user_id=user).count() == 0
        assert db.query(WorkoutSessionState).filter_by(user_id=user).count() == 0
        frozen = deepcopy(db.get(WorkoutOccurrence, session["workout_occurrence_id"]).payload)
        row = db.get(WorkoutPlan, session["plan_id"])
        changed = deepcopy(row.payload)
        changed["sessions"][0]["exercises"][0]["source_lineage"]["artifact_sha256"] = "2" * 64
        changed["sessions"][0]["exercises"][0]["authored_prescription"]["sets"][0]["rep_target"] = {"kind": "reps", "raw": "1", "min": 1, "max": 1}
        row.payload = changed; db.commit()
    correction = client.post(f"/workout/set/{data['id']}/correct", headers=headers,
        json={"command_id": str(uuid4()), "reps": 14, "weight": 25, "reason": "Synthetic correction"})
    assert correction.status_code == 200, correction.text
    assert correction.json()["session_state"]["total_logged_reps"] == 14
    undo_payload = {"command_id": str(uuid4()), "exercise_id": exercise["id"], "exercise_occurrence_id": exercise["exercise_occurrence_id"]}
    undo = client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers, json=undo_payload)
    assert undo.status_code == 200, undo.text
    assert undo.json()["session_state"]["completed_sets"] == 0
    assert client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers, json=undo_payload).json() == undo.json()
    with SessionLocal() as db:
        records = db.query(WorkoutSetLog).filter_by(user_id=user).all()
        assert len(records) == 2 and all(row.voided_at for row in records)
        assert all(row.rpe is None for row in records)  # Prescribed effort never becomes observed RPE.
        assert all(row.replay_context["planned_exercise"]["source_lineage"] == before["source_lineage"] for row in records)
        assert db.get(WorkoutOccurrence, session["workout_occurrence_id"]).payload == frozen
    assert log(client, headers, session, payload).json() == data  # No retry resurrects the void.
    retry = submission(session)
    assert log(client, headers, session, retry).status_code == 200


def test_numeric_owner_rejects_nonnumeric_prescription():
    prescribed = preserve_prescription({"reps": "AMRAP"}, 2)
    with pytest.raises(ValueError, match="receipt-only"):
        resolve_workout_log_set_plan_context(planned_exercise={"sets": 2, "rep_range": None, "authored_prescription": prescribed}, fallback_weight=20)


@pytest.mark.parametrize("parent", [None, 99])
def test_out_of_prescription_index_cannot_create_a_typed_receipt(scenario, parent):
    user, headers, client = scenario
    session = typed_plan(user)
    payload = submission(session, index=99 if parent is None else 1)
    if parent is not None:
        payload.update(parent_set_index=parent, set_kind="technique", technique={"ordinal": 1})
    response = log(client, headers, session, payload)
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 0
        assert db.query(WorkoutOccurrence).filter_by(user_id=user).count() == 0
        assert db.query(WorkoutLogCommand).filter_by(user_id=user).count() == 0


def test_schema_cannot_put_numeric_bounds_on_amrap():
    with pytest.raises(ValidationError):
        AuthoredTarget(kind="amrap", raw="AMRAP", min=8, max=12)


def test_importer_preserves_generic_rir_and_does_not_fill_absent_values():
    from importers.xlsx_to_program import ParsedSheet, parse_sheet_to_structured_sessions
    sheet = ParsedSheet(name="Full Body", rows=[
        ["Session", "Exercise", "Working Sets", "Reps", "RIR", "Rest", "Notes"],
        ["Full Body #1", "Synthetic exercise", "3", "6,10,AMRAP", "2-3", "", ""],
    ], hyperlinks={})
    result = parse_sheet_to_structured_sessions(sheet)
    exercise = result.phases[0].weeks[0].sessions[0]["exercises"][0]
    prescribed = exercise["authored_prescription"]
    assert [item["rep_target"]["raw"] for item in prescribed["sets"]] == ["6", "10", "AMRAP"]
    assert all(item["effort_target"]["kind"] == "rir" for item in prescribed["sets"])
    assert all(item["effort_target"]["min"] == 2 and item["effort_target"]["max"] == 3 for item in prescribed["sets"])
    assert exercise["rep_range"] is None and exercise["rpe_target"] is None
    assert exercise["warmup_sets"] is None and exercise["notes"] is None
    assert all(item["rest"] is None for item in prescribed["sets"])
