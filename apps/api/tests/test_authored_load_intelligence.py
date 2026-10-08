"""Completed-exposure API boundaries on explicitly verified synthetic targets."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Verify before app imports; conftest also receives an explicit URL, never defaults.
_explicit = os.environ.get("TEST_DATABASE_URL", "")
assert _explicit and os.environ.get("DATABASE_URL") == _explicit
_url = make_url(_explicit)
if _url.get_backend_name() == "sqlite":
    _root = Path(os.environ.get("M2A_LOAD_TEST_ROOT") or os.environ["CI_TEST_ROOT"]).resolve(strict=True)
    assert _root != Path("/") and Path(_url.database).resolve().is_relative_to(_root)
else:
    assert os.environ.get("M2A_POSTGRES_ISOLATED") == "1"
    assert (_url.host, _url.database, _url.username) == ("127.0.0.1", "m2a_qualification", "m2a_test")
    assert _url.port == int(os.environ["TEST_DATABASE_PORT"])
_probe = create_engine(_explicit)
with _probe.connect() as _connection:
    if _url.get_backend_name() == "sqlite":
        assert _connection.exec_driver_sql("PRAGMA database_list").first()[2] == str(Path(_url.database).resolve())
    else:
        assert tuple(_connection.execute(text("SELECT current_database(), current_user")).one()) == ("m2a_qualification", "m2a_test")
_probe.dispose()

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app import models
from app.models import User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog, WorkoutLogCommand, ExerciseState
from app.security import create_access_token
from app.workout_identity import identified_sessions
from core_engine.authored_prescription import preserve_prescription

PROGRAM = "pure_bodybuilding_phase_1_full_body"
CONTEXT = {"unit": "kg", "display_unit": "kg", "basis": "total_external", "increment": .5,
           "increment_unit": "kg", "equipment_key": "synthetic-barbell"}


@pytest.fixture
def scenario():
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
    else:
        assert os.environ.get("M2A_MIGRATED_DATABASE") == "1"
    with SessionLocal() as db:
        user = User(id=str(uuid4()), email=f"{uuid4()}@example.com", name="Synthetic load",
                    password_hash="unused", selected_program_id=PROGRAM, equipment_profile=[])
        db.add(user)
        db.commit()
        user_id = user.id
    return user_id, {"Authorization": f"Bearer {create_access_token(user_id)}"}, TestClient(app)


def plan(user, week=None, *, program=PROGRAM, variant=None, slot=1, performed_date=None):
    week = week or date.today() - timedelta(days=date.today().weekday())
    prescription = preserve_prescription({"reps": "8-12", "working_sets": "2", "early_set_rpe": "8-9",
        "last_set_rpe": "8-9", "rest": "120"}, 2)
    lineage = {"source_program_id": PROGRAM, "source_sha256": "0" * 64, "importer_sha256": "1" * 64,
        "artifact_sha256": "2" * 64, "artifact_version": "test1", "importer_version": "test1",
        "source_week": week.isocalendar().week, "source_session": 1, "source_slot": slot,
        "source_slot_id": f"synthetic:w{week.isocalendar().week}:d1:s{slot}"}
    for item in prescription["sets"]:
        item["source_set_id"] = f"{lineage['source_slot_id']}:set{item['set_index']}"
    exercise = {"id": "same-catalog", "primary_exercise_id": "same-catalog", "name": "Synthetic authored",
        "sets": 2, "rep_range": [8, 12], "recommended_working_weight": 25, "movement_pattern": "squat",
        "equipment_tags": [], "authored_prescription": prescription, "source_lineage": lineage}
    if variant:
        exercise["performed_variant"] = {"variant_id": variant, "exercise_id": variant, "load_semantics": "external_load"}
        exercise["substitution_consent"] = {"confirmed": True, "user_id": user, "variant_id": variant}
    with SessionLocal() as db:
        row = WorkoutPlan(user_id=user, week_start=week, split="full_body", phase="maintenance",
            created_at=datetime.combine(week, datetime.min.time()), payload={"program_template_id": program,
                "sessions": [{"session_id": "synthetic-load", "title": "Synthetic", "date": week.isoformat(), "exercises": [exercise]}]})
        if performed_date is not None:
            row.payload["sessions"][0].update(scheduled_date=performed_date.isoformat(),
                schedule_timezone="UTC", placement_revision=1)
        db.add(row)
        db.commit()
        return identified_sessions(row)[0]


def submit(session, index=1, **extra):
    return {"command_id": str(uuid4()), "exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"],
        "exercise_id": "same-catalog", "set_index": index, "reps": 12, "weight": 40, "rpe": 9,
        "load_context": deepcopy(CONTEXT), **extra}


def log(client, headers, session, payload):
    return client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers, json=payload)


def guidance(client, headers, session, context=CONTEXT):
    return client.post(f"/workout/{session['workout_occurrence_id']}/load-guidance", headers=headers,
        json={"exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"], "load_context": context})


def undo(client, headers, session):
    return client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers,
        json={"command_id": str(uuid4()), "exercise_id": "same-catalog",
              "exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"]})


def correct(client, headers, record, **extra):
    return client.post(f"/workout/set/{record}/correct", headers=headers,
        json={"command_id": str(uuid4()), "reps": 12, "weight": 40, "reason": "Synthetic correction", **extra})


def counts(user):
    with SessionLocal() as db:
        return tuple(db.query(model).filter_by(user_id=user).count() for model in
            (WorkoutSetLog, WorkoutLogCommand, WorkoutOccurrence, getattr(models, "AuthoredLoadState", ExerciseState)))


@pytest.mark.parametrize("dated", [True, False])
def test_out_of_order_exposures_use_owner_performed_date_with_legacy_audit_fallback(scenario, dated):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    newer = plan(user, week)
    older = plan(user, week - timedelta(days=7))
    receipts = []
    for session, weight, reps, rpe, performed_date in (
        (newer, 50, 12, 9, week), (older, 40, 7, 10, week - timedelta(days=7))
    ):
        first = log(client, headers, session, submit(session, weight=weight, reps=reps, rpe=rpe))
        assert first.status_code == 200, first.text
        if dated:
            with SessionLocal() as db:
                occurrence = db.get(WorkoutOccurrence, session["workout_occurrence_id"])
                assert occurrence.user_id == user
                occurrence.scheduled_date = performed_date
                db.commit()
        final = log(client, headers, session, submit(session, 2, weight=weight, reps=reps, rpe=rpe))
        assert final.status_code == 200, final.text
        receipts.append(first.json()["id"])
    cache_expected = ("increase", 51.5, 0) if dated else ("hold", 40, 1)
    expected = ("hold", 40, 1)
    def assert_decision(feedback):
        decision = feedback["next_exposure"]
        assert (decision["action"], decision["recommended_weight"],
            decision["evidence"]["consecutive_underperformance_count"]) == expected
        assert decision["evidence"]["completed_exposure_count"] == (1 if dated else 2)
    assert_decision(final.json()["load_intelligence"])
    changed = correct(client, headers, receipts[1], reps=6)
    assert changed.status_code == 200, changed.text
    assert_decision(changed.json()["load_intelligence"])
    with SessionLocal() as db:
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert (state["last_progression_action"], state["current_working_weight"],
            state["consecutive_under_target_exposures"]) == cache_expected
        assert state["completed_exposure_count"] == 2
    removed = undo(client, headers, newer)
    assert removed.status_code == 200, removed.text
    remaining = removed.json()["load_intelligence"]["next_exposure"]
    assert remaining["evidence"]["completed_exposure_count"] == 1
    # A partially undone latest performed occurrence stays incomplete/monitor;
    # legacy audit order still places the older completed receipt last.
    assert (remaining["action"], remaining["recommended_weight"]) == (("monitor", None) if dated else ("hold", 40))


@pytest.mark.parametrize("prior_completed", [False, True])
def test_historical_preview_and_receipts_exclude_later_dates_but_cache_retains_them(scenario, prior_completed):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    if prior_completed:
        prior = plan(user, week - timedelta(days=14), performed_date=week - timedelta(days=14))
        for index in (1, 2):
            assert log(client, headers, prior, submit(prior, index)).status_code == 200
    later = plan(user, week, performed_date=week)
    later_ids = []
    for index in (1, 2):
        response = log(client, headers, later, submit(later, index, weight=50))
        assert response.status_code == 200, response.text
        later_ids.append(response.json()["id"])
    historical = plan(user, week - timedelta(days=7), performed_date=week - timedelta(days=7))
    before = counts(user)
    preview = guidance(client, headers, historical)
    assert preview.status_code == 200, preview.text
    assert counts(user) == before  # Preview does not persist even a new occurrence.
    advice = preview.json()["next_exposure"]
    assert (advice["action"], advice["recommended_weight"]) == (("increase", 41) if prior_completed else ("monitor", None))
    assert advice["evidence"]["completed_exposure_count"] == int(prior_completed)
    assert later["workout_occurrence_id"] not in json.dumps(advice)
    assert advice["decision_trace"]["history_scope"]["cutoff_date"] == (week - timedelta(days=7)).isoformat()
    # Future amendments cannot invalidate the historical offered recommendation.
    assert correct(client, headers, later_ids[0], weight=50, reps=10).status_code == 200
    assert guidance(client, headers, historical).json()["next_exposure"] == advice
    first_payload = submit(historical, weight=35, reps=10, load_recommendation_id=advice["id"])
    first = log(client, headers, historical, first_payload)
    assert first.status_code == 200, first.text
    with SessionLocal() as db:
        captured = db.get(WorkoutSetLog, first.json()["id"]).replay_context["load_intelligence"]["offered_recommendation"]
        assert captured == advice
    final = log(client, headers, historical, submit(historical, 2, weight=35, reps=10))
    assert final.status_code == 200, final.text
    decision = final.json()["load_intelligence"]["next_exposure"]
    assert (decision["action"], decision["recommended_weight"]) == ("hold", 35)
    assert decision["evidence"]["completed_exposure_count"] == int(prior_completed) + 1
    assert later["workout_occurrence_id"] not in json.dumps(decision)
    changed = correct(client, headers, first.json()["id"], weight=35, reps=9)
    assert changed.status_code == 200, changed.text
    assert changed.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == int(prior_completed) + 1
    with SessionLocal() as db:
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert (state["last_progression_action"], state["current_working_weight"]) == ("hold", 50)
        assert state["completed_exposure_count"] == int(prior_completed) + 2
    before = counts(user)
    retry = log(client, headers, historical, first_payload)
    assert retry.status_code == 200 and retry.json() == first.json()
    assert counts(user) == before


@pytest.mark.parametrize("warmup", [False, True])
def test_undated_preview_uses_pending_utc_date_not_plan_or_warmup_date(scenario, warmup):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    prior = plan(user, week - timedelta(days=14), performed_date=date.today() - timedelta(days=1))
    later = plan(user, week + timedelta(days=7), performed_date=date.today() + timedelta(days=7))
    for session, weight in ((prior, 40), (later, 50)):
        for index in (1, 2):
            assert log(client, headers, session, submit(session, index, weight=weight)).status_code == 200
    legacy = plan(user, week - timedelta(days=7))
    if warmup:
        response = log(client, headers, legacy, submit(legacy, set_kind="warmup"))
        assert response.status_code == 200, response.text
        with SessionLocal() as db:
            # Explicit old synthetic audit evidence, before the prior work.
            db.get(WorkoutSetLog, response.json()["id"]).created_at = datetime.combine(week - timedelta(days=21), datetime.min.time())
            db.commit()
    before = counts(user)
    preview = guidance(client, headers, legacy)
    assert preview.status_code == 200, preview.text
    assert counts(user) == before
    decision = preview.json()["next_exposure"]
    assert (decision["action"], decision["recommended_weight"]) == ("increase", 41)
    assert decision["evidence"]["completed_exposure_count"] == 1
    assert later["workout_occurrence_id"] not in json.dumps(decision)
    assert decision["decision_trace"]["history_scope"]["cutoff_source"] == "pending_working_receipt_utc_date"
    with SessionLocal() as db:
        occurrence = db.get(WorkoutOccurrence, legacy["workout_occurrence_id"])
        assert occurrence is None or occurrence.scheduled_date is None


def test_low_effort_completed_work_monitors_and_corrected_effort_rebuilds_failure_streak(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    receipts = []
    for session in (plan(user, week - timedelta(days=7)), plan(user, week)):
        occurrence_receipts = []
        for index in (1, 2):
            result = log(client, headers, session, submit(session, index, reps=7, rpe=5))
            assert result.status_code == 200, result.text
            occurrence_receipts.append(result.json()["id"])
        receipts.append(occurrence_receipts)
    decision = result.json()["load_intelligence"]["next_exposure"]
    assert decision["action"] == "monitor" and decision["recommended_weight"] is None
    assert decision["evidence"]["completed_exposure_count"] == 2
    assert decision["evidence"]["consecutive_underperformance_count"] == 0
    for occurrence_receipts in reversed(receipts):
        for receipt_id in occurrence_receipts:
            result = correct(client, headers, receipt_id, reps=7, rpe=10)
            assert result.status_code == 200, result.text
        decision = result.json()["load_intelligence"]["next_exposure"]
        if occurrence_receipts == receipts[-1]:
            assert decision["action"] == "hold"
            assert decision["evidence"]["consecutive_underperformance_count"] == 1
    assert (decision["action"], decision["recommended_weight"]) == ("decrease", 39)
    assert decision["evidence"]["consecutive_underperformance_count"] == 2
    with SessionLocal() as db:
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert state["last_progression_action"] == "decrease"
        assert state["consecutive_under_target_exposures"] == 2


def test_partial_then_complete_counts_one_exposure_from_actual_load_and_preserves_source(scenario):
    user, headers, client = scenario
    session = plan(user)
    original = deepcopy(session["exercises"][0])
    first = log(client, headers, session, submit(session))
    assert first.status_code == 200, first.text
    feedback = first.json()["load_intelligence"]
    assert feedback["next_exposure"]["evidence"]["completed_exposure_count"] == 0
    assert feedback["effective_sets"][0]["rpe"] == 9
    final = log(client, headers, session, submit(session, 2))
    assert final.status_code == 200, final.text
    next_load = final.json()["load_intelligence"]["next_exposure"]
    assert next_load["evidence"]["completed_exposure_count"] == 1
    assert next_load["evidence"]["comparable_completed_exposure_count"] == 1
    assert next_load["recommended_weight"] == 41
    with SessionLocal() as db:
        assert db.query(ExerciseState).filter_by(user_id=user).count() == 0
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one()
        assert state.state["completed_exposure_count"] == 1
        frozen = db.get(WorkoutOccurrence, session["workout_occurrence_id"]).payload["exercises"][0]
        for field in ("authored_prescription", "source_lineage", "sets", "rep_range", "recommended_working_weight"):
            assert frozen[field] == original[field]


def test_preview_is_no_write_and_stale_advice_rejects_before_receipt(scenario):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    preview = guidance(client, headers, session)
    assert preview.status_code == 200, preview.text
    assert counts(user) == before
    advice = preview.json()["next_exposure"]
    assert len(advice["evidence_revision"]) == 64
    assert log(client, headers, session, submit(session)).status_code == 200
    before = counts(user)
    stale = log(client, headers, session, submit(session, 2, load_recommendation_id=advice["id"]))
    assert stale.status_code == 409
    assert counts(user) == before


def test_offered_recommendation_and_override_snapshot_remain_distinct_from_actual(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    for index in (1, 2):
        assert log(client, headers, first, submit(first, index)).status_code == 200
    second = plan(user, date(2026, 9, 14))
    offered = guidance(client, headers, second).json()["next_exposure"]
    assert offered["recommended_weight"] == 41
    response = log(client, headers, second, submit(second, weight=39,
        load_recommendation_id=offered["id"], load_override_reason="User chose attainable load"))
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        record = db.get(WorkoutSetLog, response.json()["id"])
        assert record.weight == 39 and record.rpe == 9
        assert record.replay_context["version"] == 2
        advice = record.replay_context["load_intelligence"]
        assert advice["offered_recommendation"]["recommended_weight"] == 41
        assert advice["chosen_weight"] == 39
        assert advice["override_reason"] == "User chose attainable load"
        original_advice = deepcopy(advice)
    amended = correct(client, headers, response.json()["id"], weight=38)
    assert amended.status_code == 200, amended.text
    assert amended.json()["load_intelligence"]["remaining_sets"]["recommended_weight"] == 38
    with SessionLocal() as db:
        replacement = db.get(WorkoutSetLog, amended.json()["effective_set_id"])
        assert replacement.weight == 38
        assert replacement.replay_context["load_intelligence"] == original_advice
        assert replacement.replay_context["load_intelligence"]["snapshot_scope"] == "original_log_command"
        assert replacement.replay_context["amendment"]["effective_chosen_weight"] == 38


def test_undo_retry_and_rpe_correction_rebuild_completed_evidence(scenario):
    user, headers, client = scenario
    session = plan(user)
    first_payload = submit(session)
    first = log(client, headers, session, first_payload).json()
    final_payload = submit(session, 2)
    final = log(client, headers, session, final_payload).json()
    omitted = correct(client, headers, first["id"])
    assert omitted.status_code == 200, omitted.text
    assert omitted.json()["load_intelligence"]["effective_sets"][0]["rpe"] == 9
    cleared = correct(client, headers, omitted.json()["effective_set_id"], rpe=None)
    assert cleared.status_code == 200, cleared.text
    decision = cleared.json()["load_intelligence"]["next_exposure"]
    assert decision["evidence"]["completed_exposure_count"] == 1
    assert decision["evidence"]["comparable_completed_exposure_count"] == 0
    assert decision["action"] == "monitor" and decision["recommended_weight"] is None
    undone = undo(client, headers, session)
    assert undone.status_code == 200, undone.text
    assert undone.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 0
    assert log(client, headers, session, final_payload).json() == final
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user, voided_at=None).count() == 1
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state["completed_exposure_count"] == 0


def test_correction_of_earlier_week_rebuilds_later_comparable_advice(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    first_receipts = [log(client, headers, first, submit(first, index)).json() for index in (1, 2)]
    second = plan(user, date(2026, 9, 14))
    for index in (1, 2):
        assert log(client, headers, second, submit(second, index, reps=4)).status_code == 200
    assert guidance(client, headers, second).json()["next_exposure"]["action"] == "hold"
    for receipt in first_receipts:
        changed = correct(client, headers, receipt["id"], reps=4)
        assert changed.status_code == 200, changed.text
    decision = guidance(client, headers, second).json()["next_exposure"]
    assert decision["action"] == "decrease" and decision["recommended_weight"] == 39
    assert decision["evidence"]["completed_exposure_count"] == 2
    with SessionLocal() as db:
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user).count() == 1


@pytest.mark.parametrize("extra", [{"set_kind": "warmup"}, {"parent_set_index": 1, "set_kind": "drop", "technique": {"ordinal": 1}}])
def test_warmup_and_children_do_not_complete_exposure(scenario, extra):
    user, headers, client = scenario
    session = plan(user)
    assert log(client, headers, session, submit(session, 1)).status_code == 200
    receipt = log(client, headers, session, submit(session, 2, **extra))
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 0


def test_required_index_gap_rejects_without_mutation(scenario):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    assert log(client, headers, session, submit(session, 99)).status_code == 409
    assert counts(user) == before


def test_unknown_context_and_missing_effort_never_promote_old_per_set_baseline(scenario):
    user, headers, client = scenario
    session = plan(user)
    with SessionLocal() as db:
        db.add(ExerciseState(user_id=user, exercise_id="same-catalog", current_working_weight=90, exposure_count=50))
        db.commit()
    for index in (1, 2):
        receipt = log(client, headers, session, submit(session, index, load_context=None, rpe=None))
        assert receipt.status_code == 200, receipt.text
    decision = receipt.json()["load_intelligence"]["next_exposure"]
    assert decision["action"] == "monitor" and decision["recommended_weight"] is None
    assert decision["evidence"]["completed_exposure_count"] == 1
    assert decision["evidence"]["comparable_completed_exposure_count"] == 0
    assert receipt.json()["next_working_weight"] is None
    today = client.get("/workout/today", headers=headers).json()["exercises"][0]
    assert today["recommended_working_weight"] is None
    assert today["load_recommendation_available"] is False
    with SessionLocal() as db:
        old = db.query(ExerciseState).filter_by(user_id=user).one()
        assert (old.current_working_weight, old.exposure_count) == (90, 50)


def test_confirmed_variant_and_repeated_source_slot_state_are_isolated(scenario):
    user, headers, client = scenario
    for week, variant, slot, weight in [(date(2026, 9, 7), None, 1, 40),
        (date(2026, 9, 14), "approved-variant", 1, 15), (date(2026, 9, 21), None, 2, 30)]:
        session = plan(user, week, variant=variant, slot=slot)
        for index in (1, 2):
            result = log(client, headers, session, submit(session, index, weight=weight))
            assert result.status_code == 200, result.text
    with SessionLocal() as db:
        states = db.query(models.AuthoredLoadState).filter_by(user_id=user).all()
        assert len(states) == 3
        assert sorted(row.state["completed_exposure_count"] for row in states) == [1, 1, 1]


@pytest.mark.parametrize("extra", [{"rpe": -1}, {"rpe": 10.1}, {"load_context": {**CONTEXT, "increment": 0}},
    {"load_context": {**CONTEXT, "unit": "lb"}}, {"load_context": {**CONTEXT, "basis": "guessed"}}])
def test_invalid_actual_context_rejected_before_writes(scenario, extra):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    assert log(client, headers, session, submit(session, **extra)).status_code == 422
    assert counts(user) == before


def test_foreign_guidance_cannot_read_or_mutate_another_users_evidence(scenario):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    with SessionLocal() as db:
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid", name="Other synthetic", password_hash="unused")
        db.add(other)
        db.commit()
        other_id = other.id
    foreign = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    assert guidance(client, foreign, session).status_code == 404
    assert counts(user) == before


def test_today_progress_and_summary_expose_effective_receipts_without_persisting_reads(scenario):
    user, headers, client = scenario
    session = plan(user)
    logged = log(client, headers, session, submit(session)).json()
    before = counts(user)
    today = client.get("/workout/today", headers=headers)
    progress = client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers)
    summary = client.get(f"/workout/{session['workout_occurrence_id']}/summary", headers=headers)
    for response in (today, progress, summary):
        assert response.status_code == 200, response.text
        feedback = response.json()["exercises"][0]["load_intelligence"]
        assert [(row["id"], row["weight"], row["rpe"]) for row in feedback["effective_sets"]] == [(logged["id"], 40, 9)]
    assert counts(user) == before


def test_absent_new_fields_keep_existing_generated_command_digest_and_replay(scenario):
    user, headers, client = scenario
    session = plan(user, program="full_body_v1")
    payload = submit(session)
    payload.pop("load_context")
    response = log(client, headers, session, payload)
    assert response.status_code == 200, response.text
    normalized = {key: value for key, value in payload.items() if key != "command_id"}
    normalized.update(primary_exercise_id="same-catalog", set_kind="work", parent_set_index=None, technique=None)
    normalized["weight"] = float(normalized["weight"])
    normalized["rpe"] = float(normalized["rpe"])
    expected = hashlib.sha256(json.dumps({"workout": session["workout_occurrence_id"], **normalized},
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    with SessionLocal() as db:
        assert db.query(WorkoutLogCommand).filter_by(user_id=user).one().request_digest == expected
        assert db.query(ExerciseState).filter_by(user_id=user).one().exposure_count == 1
    assert log(client, headers, session, payload).json() == response.json()


@pytest.mark.parametrize("missing", ["source_lineage", "authored_prescription"])
def test_explicit_authored_missing_source_never_uses_generated_per_set_progression(scenario, missing):
    user, headers, client = scenario
    session = plan(user)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session["plan_id"])
        value = deepcopy(row.payload)
        value["sessions"][0]["exercises"][0].pop(missing)
        row.payload = value
        db.commit()
    for index in (1, 2):
        response = log(client, headers, session, submit(session, index))
        assert response.status_code == 200, response.text
    decision = response.json()["load_intelligence"]["next_exposure"]
    assert decision["action"] == "monitor" and decision["recommended_weight"] is None
    assert decision["evidence"]["comparable_completed_exposure_count"] == 0
    with SessionLocal() as db:
        assert db.query(ExerciseState).filter_by(user_id=user).count() == 0


def test_changed_load_basis_never_reuses_remaining_set_advice(scenario):
    user, headers, client = scenario
    session = plan(user)
    assert log(client, headers, session, submit(session, reps=7, rpe=10)).status_code == 200
    changed = guidance(client, headers, session, {**CONTEXT, "basis": "per_hand"})
    assert changed.status_code == 200, changed.text
    for scope in ("next_exposure", "remaining_sets"):
        decision = changed.json()[scope]
        assert decision["action"] == "monitor" and decision["recommended_weight"] is None
        assert decision["known_baseline_weight"] is None


def test_unknown_warmup_and_child_context_cannot_anchor_working_exposure(scenario):
    user, headers, client = scenario
    session = plan(user)
    for extra in ({"set_kind": "warmup"}, {"set_kind": "drop", "parent_set_index": 1, "technique": {"ordinal": 1}}):
        response = log(client, headers, session, submit(session, load_context=None, **extra))
        assert response.status_code == 200, response.text
    for index in (1, 2):
        response = log(client, headers, session, submit(session, index))
        assert response.status_code == 200, response.text
    next_load = response.json()["load_intelligence"]["next_exposure"]
    assert next_load["evidence"]["completed_exposure_count"] == 1
    assert next_load["evidence"]["comparable_completed_exposure_count"] == 1
    assert next_load["recommended_weight"] == 41


def test_v1_typed_undo_rebuilds_new_projection_without_inventing_context(scenario):
    user, headers, client = scenario
    session = plan(user)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session["plan_id"])
        changed = deepcopy(row.payload)
        changed["sessions"][0]["exercises"][0]["authored_prescription"] = preserve_prescription(
            {"reps": "AMRAP", "early_set_rpe": "8-9", "last_set_rpe": "8-9"}, 2)
        row.payload = changed
        db.commit()
    assert log(client, headers, session, submit(session)).status_code == 200
    first = log(client, headers, session, submit(session, 2)).json()
    with SessionLocal() as db:
        record = db.get(WorkoutSetLog, first["id"])
        record.replay_context = {"version": 1, "planned_exercise": record.replay_context["planned_exercise"]}
        db.commit()
    removed = undo(client, headers, session)
    assert removed.status_code == 200, removed.text
    with SessionLocal() as db:
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state["completed_exposure_count"] == 0
        record = db.get(WorkoutSetLog, first["id"])
        assert record.replay_context == {"version": 1, "planned_exercise": record.replay_context["planned_exercise"]}


@pytest.mark.parametrize("route", ["profile", "auth"])
def test_owned_wipe_removes_only_target_projection_and_preserves_disabled_boundary(scenario, monkeypatch, route):
    from app.config import settings
    user, headers, client = scenario
    session = plan(user)
    assert log(client, headers, session, submit(session)).status_code == 200
    with SessionLocal() as db:
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid", name="Other load", password_hash="unused")
        db.add(other)
        db.commit()
        other_id = other.id
        target_email = db.get(User, user).email
    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    other_session = plan(other_id)
    assert log(client, other_headers, other_session, submit(other_session)).status_code == 200
    before = counts(user), counts(other_id)
    monkeypatch.setattr(settings, "allow_dev_wipe_endpoints", False)
    def wipe():
        return client.post("/profile/dev/wipe", headers=headers) if route == "profile" else client.post(
            "/auth/dev/wipe-user", json={"email": target_email, "confirmation": "WIPE"})
    assert wipe().status_code == 403
    assert (counts(user), counts(other_id)) == before
    monkeypatch.setattr(settings, "allow_dev_wipe_endpoints", True)
    response = wipe()
    assert response.status_code == 200, response.text
    assert counts(user) == (0, 0, 0, 0)
    assert counts(other_id) == before[1]


def test_ambiguous_active_working_ordinals_remain_retained_and_unqualified(scenario):
    user, headers, client = scenario
    session = plan(user)
    original = log(client, headers, session, submit(session)).json()
    assert log(client, headers, session, submit(session, set_kind="top")).status_code == 409
    assert log(client, headers, session, submit(session, 2)).status_code == 200
    with SessionLocal() as db:
        row = db.get(WorkoutSetLog, original["id"])
        db.add(WorkoutSetLog(user_id=user, workout_id=row.workout_id, workout_occurrence_id=row.workout_occurrence_id,
            exercise_occurrence_id=row.exercise_occurrence_id, primary_exercise_id=row.primary_exercise_id,
            exercise_id=row.exercise_id, set_index=1, reps=12, weight=40, rpe=9,
            set_kind="top", replay_context=deepcopy(row.replay_context)))
        db.commit()
    before = counts(user)
    decision = guidance(client, headers, session).json()["next_exposure"]
    assert decision["action"] == "monitor" and decision["recommended_weight"] is None
    assert "duplicate_working_set_identity" in decision["reason_codes"]
    assert len(guidance(client, headers, session).json()["effective_sets"]) == 3
    assert counts(user) == before


def test_fresh_attempt_after_full_undo_uses_effective_working_context(scenario):
    user, headers, client = scenario
    session = plan(user)
    for index in (1, 2):
        assert log(client, headers, session, submit(session, index)).status_code == 200
    for _ in range(2):
        assert undo(client, headers, session).status_code == 200
    context = {**CONTEXT, "basis": "per_hand", "equipment_key": "synthetic-dumbbells"}
    for index in (1, 2):
        response = log(client, headers, session, submit(session, index, weight=15, load_context=context))
        assert response.status_code == 200, response.text
    decision = response.json()["load_intelligence"]["next_exposure"]
    assert decision["action"] == "increase" and decision["recommended_weight"] == 15.5
    assert decision["evidence"]["completed_exposure_count"] == decision["evidence"]["comparable_completed_exposure_count"] == 1
    with SessionLocal() as db:
        states = db.query(models.AuthoredLoadState).filter_by(user_id=user).all()
        assert sorted(row.state["completed_exposure_count"] for row in states) == [0, 1]
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 4


def test_warmup_time_cannot_reorder_later_working_exposure_baseline(scenario):
    user, headers, client = scenario
    warmed = plan(user, date(2026, 9, 7))
    other = plan(user, date(2026, 9, 14))
    assert log(client, headers, warmed, submit(warmed, set_kind="warmup")).status_code == 200
    for index in (1, 2):
        assert log(client, headers, other, submit(other, index)).status_code == 200
    for index in (1, 2):
        result = log(client, headers, warmed, submit(warmed, index, weight=50))
        assert result.status_code == 200, result.text
    decision = result.json()["load_intelligence"]["next_exposure"]
    assert decision["known_baseline_weight"] == 50 and decision["recommended_weight"] == 51.5
    assert decision["evidence"]["completed_exposure_count"] == 2
    with SessionLocal() as db:
        key = decision["decision_trace"]["comparison_key"]
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user, comparison_key=key).one().state["current_working_weight"] == 51.5
        retained = db.query(models.AuthoredLoadState).filter(models.AuthoredLoadState.user_id == user,
            models.AuthoredLoadState.comparison_key != key).all()
        assert all(row.state["completed_exposure_count"] == 0 and row.state["last_progression_action"] == "monitor" for row in retained)


def test_changed_effective_cohort_resets_orphan_cache_without_deleting_receipts(scenario):
    user, headers, client = scenario
    session = plan(user)
    first = log(client, headers, session, submit(session)).json()
    second = log(client, headers, session, submit(session, 2, load_context={**CONTEXT, "basis": "per_hand"})).json()
    with SessionLocal() as db:
        prior = db.query(models.AuthoredLoadState).filter_by(user_id=user).one()
        old_key = prior.comparison_key
        assert prior.state["completed_exposure_count"] == 1
        # Synthetic retained legacy history can expose any effective subset.
        # Seed an earlier void without rewriting its receipt or captured context.
        row = db.get(WorkoutSetLog, first["id"])
        row.voided_at = datetime.now()
        row.void_source = "synthetic_retained_history"
        db.commit()
    assert log(client, headers, session, submit(session, set_kind="warmup")).status_code == 200
    with SessionLocal() as db:
        old = db.query(models.AuthoredLoadState).filter_by(user_id=user, comparison_key=old_key).one()
        assert old.state["completed_exposure_count"] == 0
        assert old.state["current_working_weight"] is None and old.state["last_progression_action"] == "monitor"
        assert db.get(WorkoutSetLog, second["id"]).voided_at is None
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 3


def _race(operations):
    barrier = Barrier(len(operations))
    def call(operation):
        barrier.wait(timeout=10)
        return operation(TestClient(app))
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(call, operation) for operation in operations]
        return [future.result(timeout=30) for future in futures]


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
def test_postgres_simultaneous_required_final_sets_count_one_exposure(scenario):
    user, headers, _ = scenario
    session = plan(user)
    payloads = [submit(session, index) for index in (1, 2)]
    results = _race([lambda client, payload=payload: log(client, headers, session, payload) for payload in payloads])
    assert [response.status_code for response in results] == [200, 200]
    assert counts(user) == (2, 2, 1, 1)
    with SessionLocal() as db:
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert state["completed_exposure_count"] == state["qualified_exposure_count"] == 1
        assert state["current_working_weight"] == 41


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
@pytest.mark.parametrize("changed", [False, True])
def test_postgres_same_command_returns_original_or_payload_conflict(scenario, changed):
    user, headers, _ = scenario
    session = plan(user)
    payload = submit(session)
    second = {**payload, "reps": 11} if changed else deepcopy(payload)
    results = _race([lambda client: log(client, headers, session, payload),
                     lambda client: log(client, headers, session, second)])
    assert sorted(response.status_code for response in results) == ([200, 409] if changed else [200, 200])
    if not changed:
        assert results[0].json() == results[1].json()
    assert counts(user) == (1, 1, 1, 1)
    with SessionLocal() as db:
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state["completed_exposure_count"] == 0


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
def test_postgres_correction_racing_completion_rebuilds_once_with_actual_effort(scenario):
    user, headers, client = scenario
    session = plan(user)
    original_payload = submit(session)
    original = log(client, headers, session, original_payload).json()
    with SessionLocal() as db:
        audit_time = db.get(WorkoutSetLog, original["id"]).created_at
    results = _race([lambda other: log(other, headers, session, submit(session, 2)),
                     lambda other: correct(other, headers, original["id"], rpe=None)])
    assert [response.status_code for response in results] == [200, 200]
    assert counts(user) == (3, 3, 1, 1)
    with SessionLocal() as db:
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert state["completed_exposure_count"] == 1 and state["qualified_exposure_count"] == 0
        assert state["last_progression_action"] == "monitor" and state["current_working_weight"] is None
        replacement = db.query(WorkoutSetLog).filter_by(supersedes_id=original["id"]).one()
        assert replacement.created_at == audit_time and replacement.rpe is None
    assert log(client, headers, session, original_payload).json() == original


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
def test_postgres_competing_corrections_keep_one_effective_replacement(scenario):
    user, headers, client = scenario
    session = plan(user)
    first = log(client, headers, session, submit(session)).json()
    assert log(client, headers, session, submit(session, 2)).status_code == 200
    results = _race([lambda other: correct(other, headers, first["id"], weight=37),
                     lambda other: correct(other, headers, first["id"], weight=39)])
    assert sorted(response.status_code for response in results) == [200, 409]
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(supersedes_id=first["id"]).count() == 1
        assert db.query(WorkoutSetLog).filter_by(user_id=user, voided_at=None).count() == 2
        state = db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state
        assert state["completed_exposure_count"] == 1 and state["qualified_exposure_count"] == 0
