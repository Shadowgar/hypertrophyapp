"""Real Authored dated-plan conversion, using only disposable scenario accounts."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest

from test_selected_date_scheduling import scenario, request_dates, current_monday
from app.database import SessionLocal
from app.flexible_source import native_source
from app.models import User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog, TrainingSequence


PHASE1 = "pure_bodybuilding_phase_1_full_body"
PHASE2 = "pure_bodybuilding_phase_2_full_body"


def dated_plan(scenario, program_id=PHASE1):
    uid, headers, client = scenario
    generated = client.post('/plan/generate-week', headers=headers,
        json=request_dates(current_monday(), phase=program_id))
    assert generated.status_code == 200, generated.text
    assert len(generated.json()["sessions"]) == 3
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=uid).one()
        return row.id, deepcopy(row.payload), generated.json()


def switch_preview(client, headers, plan_id, program_id=PHASE1):
    request = {"program_id": program_id, "timezone": "America/New_York",
        "expected_sessions_per_week": 3, "switch_plan_id": plan_id}
    response = client.post('/training/enroll/preview', headers=headers, json=request)
    assert response.status_code == 200, response.text
    return request, response.json()


def assert_no_conversion(uid, plan_id, original):
    with SessionLocal() as db:
        assert db.query(TrainingSequence).filter_by(user_id=uid).count() == 0
        assert db.get(WorkoutPlan, plan_id).payload == original


@pytest.mark.parametrize("program_id,auto", [(PHASE1, False), (PHASE2, False), (PHASE1, True)])
def test_switch_retains_redistributed_history_and_materializes_native_fifty_sessions(scenario, program_id, auto):
    uid, headers, client = scenario
    plan_id, original, _ = dated_plan(scenario, program_id)
    if auto:
        with SessionLocal() as db:
            user = db.get(User, uid)
            user.selected_program_id = None
            user.program_selection_mode = "auto"
            db.commit()
    discovery = client.post('/training/enroll/preview', headers=headers, json={
        "program_id": program_id, "timezone": "America/New_York", "expected_sessions_per_week": 3})
    assert discovery.status_code == 200, discovery.text
    assert discovery.json()["legacy_plan_id"] == plan_id
    assert discovery.json()["available"] is False
    with SessionLocal() as db:
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count() == 0
    request, preview = switch_preview(client, headers, plan_id, program_id)
    assert preview["available"] is True, preview
    command_id = str(uuid4())
    confirmed = client.post('/training/enroll', headers=headers, json={**request,
        "preview_digest": preview["digest"], "command_id": command_id, "confirmed": True})
    assert confirmed.status_code == 200, confirmed.text
    state = confirmed.json()
    admitted = native_source(program_id)
    with SessionLocal() as db:
        retained = db.get(WorkoutPlan, plan_id).payload
        assert retained["sessions"] == original["sessions"]
        assert {k: v for k, v in retained.items() if k not in ("schedule", "flexible_supersession")} == {
            k: v for k, v in original.items() if k != "schedule"}
        assert retained["schedule"] == {**original["schedule"], "mode": "selected_dates_superseded_v1"}
        assert retained["flexible_supersession"] == {"sequence_id": state["sequence_id"],
            "command_id": command_id, "original_schedule": original["schedule"], "prescription_retained": True}
        sequences = db.query(TrainingSequence).filter_by(user_id=uid, state="active").all()
        assert len(sequences) == 1
        assert sequences[0].program_id == program_id
        occurrences = db.query(WorkoutOccurrence).filter_by(user_id=uid,
            sequence_id=state["sequence_id"]).order_by(WorkoutOccurrence.source_position).all()
        assert len(occurrences) == 50
        assert [row.source_position for row in occurrences] == list(range(50))
        for row, item in zip(occurrences, admitted["items"]):
            assert row.plan_id is None and row.week_start is None and row.scheduled_date is None
            assert row.execution_state == "planned"
            assert row.source_week == item["source_week"]
            assert row.source_session == item["source_session"]
            assert row.payload["name"] == item["session"]["name"]
            actual = deepcopy(row.payload["exercises"])
            for exercise in actual:
                exercise.pop("exercise_occurrence_id")
                exercise.pop("execution_slot")
            assert actual == item["session"]["exercises"]
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0
        if auto:
            assert db.get(User, uid).selected_program_id is None
            assert db.get(User, uid).program_selection_mode == "auto"


@pytest.mark.parametrize("field,value", [
    ("id", "unapproved_performed_exercise"),
    ("primary_exercise_id", "different_primary_identity"),
    ("rep_range", [1, 2]),
    ("load_semantics", "assistance"),
    ("execution_modifiers", {"unreviewed_performed_load_basis": "per_hand"}),
])
def test_changed_execution_identity_or_semantics_cannot_hide_behind_source_lineage(scenario, field, value):
    uid, headers, client = scenario
    plan_id, _, _ = dated_plan(scenario)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, plan_id)
        changed = deepcopy(row.payload)
        changed["sessions"][0]["exercises"][0][field] = value
        row.payload = changed
        db.commit()
    request, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is False, preview
    assert any(blocker["code"] == "legacy_source_mismatch" for blocker in preview["blockers"])
    denied = client.post('/training/enroll', headers=headers, json={**request,
        "preview_digest": preview["digest"], "command_id": str(uuid4()), "confirmed": True})
    assert denied.status_code == 409, denied.text
    assert_no_conversion(uid, plan_id, changed)


def test_confirmed_consent_snapshot_without_performed_sets_blocks_conversion(scenario):
    uid, headers, client = scenario
    plan_id, original, rendered = dated_plan(scenario)
    session = rendered["sessions"][0]
    exercise = session["exercises"][0]
    body = {"exercise_id": exercise["id"], "exercise_occurrence_id": exercise["exercise_occurrence_id"],
        "expected_revision": 0, "expected_source_lineage": exercise["source_lineage"],
        "action": "report", "reason": "pain", "command_id": str(uuid4())}
    path = f'/workout/{session["workout_occurrence_id"]}/authored-substitution'
    reported = client.post(path, headers=headers, json=body)
    assert reported.status_code == 200, reported.text
    constraint = reported.json()["exercise"]["authored_constraint"]
    assert constraint["allowed_alternatives"]
    consent = client.post(path, headers=headers, json={**body, "action": "confirm",
        "expected_revision": constraint["revision"], "option_id": constraint["allowed_alternatives"][0]["option_id"],
        "command_id": str(uuid4())})
    assert consent.status_code == 200, consent.text
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0
        snapshot = db.query(WorkoutOccurrence).filter_by(user_id=uid).one()
        assert snapshot.payload["exercises"][0]["substitution_consent"]["confirmed"] is True
    _, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is False
    assert any(blocker["code"] == "legacy_started" for blocker in preview["blockers"])
    assert_no_conversion(uid, plan_id, original)


@pytest.mark.parametrize("mutation", ["source_order", "alternative_permission"])
def test_conversion_rejects_reordered_source_or_changed_alternative_permission(scenario, mutation):
    uid, headers, client = scenario
    plan_id, _, _ = dated_plan(scenario)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, plan_id)
        changed = deepcopy(row.payload)
        exercises = changed["sessions"][0]["exercises"]
        if mutation == "source_order":
            exercises[0], exercises[1] = exercises[1], exercises[0]
        else:
            alternatives = exercises[0]["source_approved_alternatives"]
            assert alternatives
            alternatives[0]["permission"]["source_option_value"] = "Unapproved changed permission"
        row.payload = changed
        db.commit()
    request, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is False, preview
    assert any(blocker["code"] == "legacy_source_mismatch" for blocker in preview["blockers"])
    denied = client.post('/training/enroll', headers=headers, json={**request,
        "preview_digest": preview["digest"], "command_id": str(uuid4()), "confirmed": True})
    assert denied.status_code == 409, denied.text
    assert_no_conversion(uid, plan_id, changed)


def test_recorded_work_blocks_conversion_and_preserves_receipt(scenario):
    uid, headers, client = scenario
    plan_id, original, rendered = dated_plan(scenario)
    session = rendered["sessions"][0]
    exercise = session["exercises"][0]
    logged = client.post(f'/workout/{session["workout_occurrence_id"]}/log-set', headers=headers, json={
        "command_id": str(uuid4()), "exercise_id": exercise["id"],
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "set_index": 1,
        "reps": 8, "weight": 20, "set_kind": "work"})
    assert logged.status_code == 200, logged.text
    _, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is False
    assert any(blocker["code"] == "legacy_started" for blocker in preview["blockers"])
    assert_no_conversion(uid, plan_id, original)
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 1


def test_current_and_future_outstanding_reservations_require_reconciliation(scenario):
    uid, headers, client = scenario
    plan_id, original, _ = dated_plan(scenario)
    future_request = request_dates(current_monday() + timedelta(days=7))
    previewed = client.post('/plan/selected-dates/preview', headers=headers, json=future_request)
    assert previewed.status_code == 200, previewed.text
    future = client.post('/plan/generate-week', headers=headers, json={**future_request,
        "expected_preview_digest": previewed.json()["schedule"]["preview_digest"]})
    assert future.status_code == 200, future.text
    _, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is False
    assert any(blocker["code"] == "legacy_reservation_conflict" for blocker in preview["blockers"])
    assert_no_conversion(uid, plan_id, original)
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count() == 2


def test_changed_placement_invalidates_reviewed_conversion_without_supersession(scenario):
    uid, headers, client = scenario
    plan_id, _, _ = dated_plan(scenario)
    request, preview = switch_preview(client, headers, plan_id)
    assert preview["available"] is True, preview
    moved = client.post('/plan/generate-week', headers=headers,
        json=request_dates(current_monday(), offsets=(0, 2, 5), revision=1))
    assert moved.status_code == 200, moved.text
    denied = client.post('/training/enroll', headers=headers, json={**request,
        "preview_digest": preview["digest"], "command_id": str(uuid4()), "confirmed": True})
    assert denied.status_code == 409, denied.text
    with SessionLocal() as db:
        assert db.query(TrainingSequence).filter_by(user_id=uid).count() == 0
        retained = db.get(WorkoutPlan, plan_id)
        assert retained.placement_revision == 2
        assert "flexible_supersession" not in retained.payload
        assert retained.payload["schedule"]["mode"] == "selected_dates_v1"
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0
