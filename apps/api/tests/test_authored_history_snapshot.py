"""Response-local history reuse on explicitly isolated synthetic targets."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event

# This module verifies the explicit disposable DB identity before app imports.
from test_authored_load_intelligence import (
    scenario, plan, CONTEXT, log, submit, correct, undo, counts,
    SessionLocal, engine, User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog,
)
from app.workout_identity import identified_sessions
from app import workout_load_state as load_state
from app.workout_identity import resolve_occurrence
from fastapi import HTTPException
from authored_history_baseline import legacy_project_authored_load_feedback


def multi_plan(user, week=None, *, performed_date=None, exercises=3):
    week = week or date.today() - timedelta(days=date.today().weekday())
    session = plan(user, week, performed_date=performed_date, warm_up_sets="2")
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user, week_start=week).order_by(WorkoutPlan.created_at.desc()).first()
        payload = deepcopy(row.payload)
        original = payload["sessions"][0]["exercises"][0]
        slots = []
        for slot in range(1, exercises + 1):
            ex = deepcopy(original)
            ex.update(id=f"synthetic-history-{slot}", primary_exercise_id=f"synthetic-history-{slot}",
                      name=f"Synthetic history slot {slot}", rest="120", primary_muscles=["quads"])
            ex["source_lineage"].update(source_slot=slot, source_slot_id=f"synthetic:session1:slot{slot}")
            for item in ex["authored_prescription"]["sets"]:
                item["source_set_id"] = f"synthetic:session1:slot{slot}:set{item['set_index']}"
            slots.append(ex)
        payload["sessions"][0]["exercises"] = slots
        row.payload = payload
        db.commit()
        return identified_sessions(row)[0]


def add_history(user_id, template, count):
    """Bulk benchmark fixtures only; never a production importer or receipt writer."""
    with SessionLocal() as db:
        occurrences, receipts = [], []
        for index in range(count):
            day = date.today() - timedelta(days=count - index)
            when = datetime.combine(day, datetime.min.time()).replace(hour=9)
            oid = str(uuid4())
            payload = deepcopy(template)
            payload.update(workout_occurrence_id=oid, date=day.isoformat())
            for slot, ex in enumerate(payload["exercises"], 1):
                ex["exercise_occurrence_id"] = f"{oid}:slot{slot}"
                for ordinal in (1, 2):
                    receipts.append(WorkoutSetLog(id=str(uuid4()), user_id=user_id,
                        workout_id=template["session_id"], workout_occurrence_id=oid,
                        exercise_occurrence_id=ex["exercise_occurrence_id"],
                        primary_exercise_id=ex["id"], exercise_id=ex["id"], set_index=ordinal,
                        reps=12, weight=40, rpe=9, set_kind="work", created_at=when,
                        replay_context={"version": 2, "load_intelligence": {"load_context": deepcopy(CONTEXT)}}))
            occurrences.append(WorkoutOccurrence(id=oid, user_id=user_id, plan_id=str(uuid4()),
                week_start=day-timedelta(days=day.weekday()), scheduled_date=day, session_slot=1,
                workout_id=template["session_id"], program_id="pure_bodybuilding_phase_1_full_body",
                payload=payload, created_at=when))
        db.add_all(occurrences)
        db.flush()
        db.add_all(receipts)
        db.commit()


@pytest.mark.parametrize("route", ["today", "progress", "summary"])
def test_multi_exercise_response_reconstructs_history_once(scenario, monkeypatch, route):
    user, headers, client = scenario
    session = multi_plan(user, performed_date=date.today())
    add_history(user, session, 2)
    original = load_state._all_groups
    scans, queries, keys = [], [], []
    original_key = load_state._projection_key
    def measured(db, owner):
        result = original(db, owner)
        scans.append(len(result))
        return result
    def query(_conn, _cursor, sql, *_args):
        compact = " ".join(sql.lower().split())
        if "from workout_set_logs join workout_occurrences" in compact or (
                "from workout_occurrences" in compact and "program_id in" in compact):
            queries.append(compact)
    def measured_key(exposure):
        keys.append(exposure["exercise_occurrence_id"])
        return original_key(exposure)
    monkeypatch.setattr(load_state, "_all_groups", measured)
    monkeypatch.setattr(load_state, "_projection_key", measured_key)
    event.listen(engine, "before_cursor_execute", query)
    try:
        path = "/workout/today" if route == "today" else f"/workout/{session['workout_occurrence_id']}/{route}"
        response = client.get(path, headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", query)
    assert response.status_code == 200, response.text
    assert len(response.json()["exercises"]) == 3
    assert len(scans) == 1
    assert len(queries) == 2
    assert len(keys) == 9  # Six historical groups once, plus three current projections.


@pytest.mark.parametrize("case,completed", [
    ("complete", 2), ("incomplete", 1), ("warmup_only", 1),
    ("corrected", 2), ("voided", 1), ("variant", 1), ("equipment", 1),
    ("source_slot", 1), ("unknown_rpe", 2), ("later_date", 1), ("older_target", 1),
    ("legacy_date", 2),
])
def test_snapshot_matches_pre_optimization_decisions_and_traces(scenario, case, completed):
    uid, _headers, _client = scenario
    session = multi_plan(uid, performed_date=date.today())
    add_history(uid, session, 2)
    with SessionLocal() as db:
        historical = db.query(WorkoutOccurrence).filter_by(user_id=uid).order_by(WorkoutOccurrence.scheduled_date).all()
        newest = historical[-1]
        ex = newest.payload["exercises"][0]
        rows = db.query(WorkoutSetLog).filter_by(user_id=uid, workout_occurrence_id=newest.id,
            exercise_occurrence_id=ex["exercise_occurrence_id"]).order_by(WorkoutSetLog.set_index).all()
        if case in {"incomplete", "voided", "corrected"}:
            for row in (rows if case == "voided" else rows[1:]):
                row.voided_at = datetime.now()
                row.void_source = "synthetic_test"
            if case == "corrected":
                root = rows[1]
                db.add(WorkoutSetLog(user_id=uid, workout_id=root.workout_id,
                    workout_occurrence_id=root.workout_occurrence_id, exercise_occurrence_id=root.exercise_occurrence_id,
                    primary_exercise_id=root.primary_exercise_id, exercise_id=root.exercise_id,
                    set_index=2, set_kind="work", reps=10, weight=40, rpe=8, supersedes_id=root.id,
                    created_at=root.created_at, amended_at=datetime.now(), replay_context=deepcopy(root.replay_context)))
        if case == "warmup_only":
            for row in rows: row.set_kind = "warmup"
        if case == "unknown_rpe": rows[1].rpe = None
        if case == "equipment":
            for row in rows:
                context = deepcopy(row.replay_context)
                context["load_intelligence"]["load_context"]["equipment_key"] = "different-synthetic-equipment"
                row.replay_context = context
        if case in {"variant", "source_slot"}:
            payload = deepcopy(newest.payload)
            target = payload["exercises"][0]
            if case == "variant": target["performed_variant"] = {"id":"different-performed-variant","load_semantics":"external_load"}
            else: target["source_lineage"]["source_slot"] = 99
            newest.payload = payload
        if case == "later_date": newest.scheduled_date = date.today() + timedelta(days=1)
        if case == "legacy_date": newest.scheduled_date = None
        db.commit()
        user = db.get(User, uid)
        occurrence, frozen = resolve_occurrence(db, uid, session["workout_occurrence_id"],
            db.query(WorkoutPlan).filter_by(user_id=uid).all())
        if case == "older_target": occurrence.scheduled_date = date.today() - timedelta(days=2)
        preserved = deepcopy(frozen)
        baseline = [legacy_project_authored_load_feedback(db, user=user, occurrence=occurrence,
            exercise=exercise, supplied_context=CONTEXT) for exercise in frozen["exercises"]]
        fresh = [load_state.project_authored_load_feedback(db, user=user, occurrence=occurrence,
            exercise=exercise, supplied_context=CONTEXT) for exercise in frozen["exercises"]]
        snapshot = load_state.load_authored_history_snapshot(db, user=user)
        shared = [load_state.project_authored_load_feedback(db, user=user, occurrence=occurrence,
            exercise=exercise, supplied_context=CONTEXT, history_snapshot=snapshot) for exercise in frozen["exercises"]]
        # Snapshot reuse must preserve the entire current response, including
        # calibration advice IDs and traces, not only the pre-amendment fields.
        assert shared == fresh
        for current, legacy in zip(shared, baseline, strict=True):
            assert set(current) == set(legacy) | {"calibration", "initial_estimate"}
            # Keep every legacy field, ID, revision, reason and warm-up trace
            # exactly equal. Only the two explicitly added fields are separate.
            assert {key: current[key] for key in legacy} == legacy
            assert current["calibration"] is None
            initial = current["initial_estimate"]
            assert initial["scope"] == "initial_calibration"
            assert initial["status"] == "unavailable"
            assert initial["reason_codes"] == ["effective_history_takes_precedence"]
            assert initial["recommended_weight"] is None
            assert initial["recommended_working_weight"] is None
            assert initial["prefill_available"] is False
            assert initial["reported_1rm"] is None
            assert initial["estimated_1rm"] is None
            assert initial["decision_trace"]["has_current_work"] is False
            assert initial["decision_trace"]["has_effective_history"] is True
            assert initial["decision_trace"]["calibration_id"] is None
            assert initial["decision_trace"]["calibration_revision"] is None
        assert shared[0]["next_exposure"]["evidence"]["completed_exposure_count"] == completed
        assert frozen == preserved
        # A sibling source slot never inherits the modified first slot's evidence.
        assert shared[1]["next_exposure"]["evidence"]["completed_exposure_count"] == (1 if case in {"later_date","older_target"} else 2)


def test_snapshot_cannot_cross_users_or_database_sessions(scenario):
    uid, _headers, _client = scenario
    session = multi_plan(uid, performed_date=date.today())
    with SessionLocal() as first, SessionLocal() as second:
        owner = first.get(User, uid)
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.com", name="Synthetic other user",
            password_hash="unused", equipment_profile=[])
        first.add(other)
        first.commit()
        occurrence, frozen = resolve_occurrence(first, uid, session["workout_occurrence_id"],
            first.query(WorkoutPlan).filter_by(user_id=uid).all())
        snapshot = load_state.load_authored_history_snapshot(first, user=owner)
        for db, user in ((first,other),(second,second.get(User,uid))):
            with pytest.raises(HTTPException) as error:
                load_state.project_authored_load_feedback(db,user=user,occurrence=occurrence,
                    exercise=frozen["exercises"][0],history_snapshot=snapshot)
            assert error.value.status_code == 409


def test_new_response_sees_correction_and_undo_and_retains_immutable_retries(scenario):
    uid, headers, client = scenario
    monday = date.today()-timedelta(days=date.today().weekday())
    old = multi_plan(uid, monday-timedelta(days=7), performed_date=date.today()-timedelta(days=7))
    target = multi_plan(uid, monday, performed_date=date.today())
    payloads, receipts = [], []
    for index in (1,2):
        payload = submit(old,index,exercise_id=old["exercises"][0]["id"])
        result = log(client,headers,old,payload)
        assert result.status_code == 200,result.text
        payloads.append(payload);receipts.append(result.json())
    warmup = submit(target,exercise_id=target["exercises"][0]["id"],set_kind="warmup",reps=8,weight=20,rpe=None)
    assert log(client,headers,target,warmup).status_code == 200
    path = f"/workout/{target['workout_occurrence_id']}/progress"
    before = client.get(path,headers=headers).json()["exercises"]
    correction_payload = {"command_id":str(uuid4()),"reps":8,"weight":40,"rpe":8,"reason":"Synthetic correction"}
    correction = client.post(f"/workout/set/{receipts[0]['id']}/correct",headers=headers,json=correction_payload)
    assert correction.status_code == 200,correction.text
    after = client.get(path,headers=headers).json()["exercises"]
    assert after[0]["load_intelligence"]["next_exposure"]["id"] != before[0]["load_intelligence"]["next_exposure"]["id"]
    assert after[1:]==before[1:]
    saved_counts = counts(uid)
    retry = client.post(f"/workout/set/{receipts[0]['id']}/correct",headers=headers,json=correction_payload)
    assert retry.json() == correction.json()
    assert log(client,headers,old,payloads[0]).json() == receipts[0]
    assert counts(uid) == saved_counts
    result = client.post(f"/workout/{old['workout_occurrence_id']}/undo-last-set",headers=headers,
        json={"command_id":str(uuid4()),"exercise_id":old["exercises"][0]["id"],
              "exercise_occurrence_id":old["exercises"][0]["exercise_occurrence_id"]})
    assert result.status_code == 200,result.text
    after_undo = client.get(path,headers=headers).json()["exercises"][0]["load_intelligence"]
    assert after_undo["next_exposure"]["id"] != after[0]["load_intelligence"]["next_exposure"]["id"]
    assert after_undo["next_exposure"]["evidence"]["completed_exposure_count"] == 0
    assert len(after_undo["effective_sets"]) == 1
    assert after_undo["effective_sets"][0]["set_kind"] == "warmup"
