"""Characterize EXISTING Authored guidance; no proposed formula is implemented.

Run only after verifying the named disposable PostgreSQL container/target.
Supply isolated DATABASE_URL, TEST_DATABASE_URL and synthetic JWT_SECRET;
PYTHONPATH must select this checkout's apps/api and packages/core-engine.
Creates unique synthetic accounts/plans/receipts; never resets/deletes data.
"""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = os.environ.get("TEST_DATABASE_URL", "")
assert url and url == os.environ.get("DATABASE_URL"), "Explicit isolated URLs required"
target = make_url(url)
assert (target.get_backend_name(), target.host, target.port, target.database, target.username) == (
    "postgresql", "127.0.0.1", 55418, "m2a_qualification", "m2a_test"
), "Refusing a different target"
assert os.environ.get("M2A_POSTGRES_ISOLATED") == "1"
probe = create_engine(url)
with probe.connect() as connection:
    assert tuple(connection.execute(text("select current_database(), current_user")).one()) == (
        "m2a_qualification", "m2a_test"
    )
probe.dispose()

from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.program_loader import load_program_template
from app.security import create_access_token
from app.workout_identity import identified_sessions

PROGRAM = "pure_bodybuilding_phase_1_full_body"
original = load_program_template(PROGRAM)["sessions"][0]["exercises"][0]
assert original["id"] == "cross_body_lat_pull_around"
assert len(original["authored_prescription"]["sets"]) == 3
assert original["rep_range"] == [10, 12]
# The template precedes the plan adapter's required numeric presentation field.
# Zero is an unknown-load compatibility placeholder, NOT suggested/performed load.
# The load owner must abstain rather than promote this field into evidence.
original["recommended_working_weight"] = 0.0
source_digest = lambda: hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()
before_digest = source_digest()
prescription_digest = hashlib.sha256(json.dumps(original["authored_prescription"], sort_keys=True).encode()).hexdigest()
monday = date.today() - timedelta(days=date.today().weekday())
context = {"unit": "kg", "display_unit": "kg", "basis": "machine_stack",
           "equipment_key": "synthetic-cable-A:attachment-1:unilateral-stack",
           "increment": .5, "increment_unit": "kg"}
client = TestClient(app)


def account():
    uid = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=uid, email=f"starting-load-{uid}@example.com", name="Synthetic characterization",
            password_hash="unused", selected_program_id=PROGRAM,
            equipment_profile=original.get("equipment_tags") or [], movement_restrictions=[]))
        db.commit()
    return uid, {"Authorization": f"Bearer {create_access_token(uid)}"}


def plan(uid, when):
    with SessionLocal() as db:
        row = WorkoutPlan(user_id=uid, week_start=when, split="full_body", phase="maintenance",
            payload={"program_template_id": PROGRAM, "sessions": [{"session_id": "synthetic-cross-body",
                "title": "Synthetic source-preserving occurrence", "date": when.isoformat(),
                "scheduled_date": when.isoformat(), "schedule_timezone": "UTC", "placement_revision": 1,
                "exercises": [deepcopy(original)]}]})
        db.add(row)
        db.commit()
        return identified_sessions(row)[0]


def guidance(headers, session, supplied):
    response = client.post(f"/workout/{session['workout_occurrence_id']}/load-guidance", headers=headers,
        json={"exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"],
              "load_context": supplied})
    assert response.status_code == 200, response.text
    return response.json()


def record(headers, session, index, supplied, effort=True):
    response = client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers, json={
        "command_id": str(uuid4()), "exercise_id": original["id"],
        "exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"],
        "set_index": index, "reps": 11, "weight": 40,
        "rpe": (7.5 if index < 3 else 8.5) if effort else None, "load_context": supplied})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def observed(feedback):
    d = feedback["next_exposure"]
    return {key: d[key] for key in ("action", "recommended_weight", "prefill_available", "reason_codes", "evidence")}


results = {}
uid, headers = account()
current = plan(uid, monday)
empty = guidance(headers, current, context)
assert empty["next_exposure"]["recommended_weight"] is None
assert "no_completed_exposure_evidence" in empty["next_exposure"]["reason_codes"]
results["no_history_explicit_setup"] = observed(empty)
for index in (1, 2):
    record(headers, current, index, context)
partial = guidance(headers, current, context)
assert "incomplete_exposure" in partial["next_exposure"]["reason_codes"]
assert partial["next_exposure"]["evidence"]["completed_exposure_count"] == 0
assert partial["remaining_sets"]["recommended_weight"] == 40
results["two_of_three_working_sets"] = observed(partial)
results["partial_remaining_set_authority"] = {
    "action": partial["remaining_sets"]["action"], "recommended_weight": 40,
    "origin": "actual_current_sets_not_initial_calibration"}

uid2, h2 = account()
prior = plan(uid2, monday - timedelta(days=7))
receipt_ids = [record(h2, prior, i, context) for i in (1, 2, 3)]
future = plan(uid2, monday)
qualified = guidance(h2, future, context)
assert qualified["next_exposure"]["action"] == "hold"
assert qualified["next_exposure"]["recommended_weight"] == 40
assert qualified["next_exposure"]["evidence"]["comparable_completed_exposure_count"] == 1
results["completed_comparable_history"] = observed(qualified)
assert guidance(h2, future, {**context, "display_unit": "lb"})["next_exposure"]["recommended_weight"] == 40
assert guidance(h2, future, context)["next_exposure"] == qualified["next_exposure"]
results["display_unit_round_trip_and_repeat"] = "same canonical 40 kg and identical repeated decision"
for name, supplied in (
    ("incompatible_machine", {**context, "equipment_key": "synthetic-cable-B"}),
    ("missing_load_basis", {**context, "basis": "unknown"}),
    ("missing_machine_identity", {**context, "equipment_key": None}),
):
    result = guidance(h2, future, supplied)
    assert result["next_exposure"]["recommended_weight"] is None
    results[name] = observed(result)
foreign = client.post(f"/workout/{future['workout_occurrence_id']}/load-guidance", headers=headers,
    json={"exercise_occurrence_id": future["exercises"][0]["exercise_occurrence_id"], "load_context": context})
assert foreign.status_code == 404, foreign.text
results["foreign_account"] = "404; no cross-account evidence returned"

correction = {"command_id": str(uuid4()), "reps": 11, "weight": 35, "rpe": 7.5,
              "reason": "Synthetic mixed-load characterization"}
for _ in range(2):
    changed = client.post(f"/workout/set/{receipt_ids[0]}/correct", headers=h2, json=correction)
    assert changed.status_code == 200, changed.text
mixed = guidance(h2, future, context)
assert "mixed_working_loads" in mixed["next_exposure"]["reason_codes"]
results["after_correction_and_exact_retry"] = observed(mixed)
with SessionLocal() as db:
    assert db.query(WorkoutSetLog).filter_by(user_id=uid2).count() == 4
    assert db.get(WorkoutSetLog, receipt_ids[0]).voided_at is not None
    assert db.query(WorkoutSetLog).filter_by(user_id=uid2, voided_at=None).count() == 3
undone = client.post(f"/workout/{prior['workout_occurrence_id']}/undo-last-set", headers=h2,
    json={"command_id": str(uuid4()), "exercise_id": original["id"],
          "exercise_occurrence_id": prior["exercises"][0]["exercise_occurrence_id"]})
assert undone.status_code == 200, undone.text
after_void = guidance(h2, future, context)
assert "incomplete_exposure" in after_void["next_exposure"]["reason_codes"]
results["after_void"] = observed(after_void)

uid3, h3 = account()
missing = plan(uid3, monday - timedelta(days=7))
for i in (1, 2, 3):
    record(h3, missing, i, context, effort=False)
missing_current = plan(uid3, monday)
effort = guidance(h3, missing_current, context)
assert "actual_rpe_missing" in effort["next_exposure"]["reason_codes"]
results["complete_but_missing_actual_effort"] = observed(effort)
assert source_digest() == before_digest
results["source_prescription_unchanged"] = before_digest
with SessionLocal() as db:
    assert db.query(WorkoutSetLog).filter_by(user_id=uid2).count() == 4
    assert db.query(WorkoutSetLog).filter_by(user_id=uid2, voided_at=None).count() == 2
    snapshots = db.query(WorkoutOccurrence).filter(WorkoutOccurrence.user_id.in_([uid, uid2, uid3])).all()
    assert snapshots
    for snapshot in snapshots:
        assert snapshot.payload["exercises"][0]["authored_prescription"] == original["authored_prescription"]
results["all_created_frozen_prescriptions_unchanged"] = prescription_digest
results["history_retention"] = "4 rows retained after one correction replayed twice and one undo; 2 effective"
print(json.dumps({"application_revision": "b3844398b50a64311f99ccf74411801bbd88225c",
    "kind": "existing behavior characterization; proposed initial formula NOT implemented",
    "target": {"host": "127.0.0.1", "port": 55418, "database": "m2a_qualification", "user": "m2a_test"},
    "cases": results}, indent=2))
