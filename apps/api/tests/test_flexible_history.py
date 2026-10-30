"""Flexible history and load dating on the explicitly isolated test target."""
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core_engine.history_status import calendar_statuses


def flexible_session(state="finished", rows=None):
    return {"session_id": "source-session", "workout_occurrence_id": "flex-occurrence",
        "sequence_id": "sequence", "title": "Source workout", "execution_state": state,
        "actual_dates": ["2026-10-19", "2026-10-27"],
        "advancement": {"operation": "finish", "coverage": [["slot", 1], ["slot", 2]],
            "missing": [], "local_day": "2026-10-27"},
        "exercises": [{"id": "press", "exercise_occurrence_id": "slot", "sets": 2}],
        "coverage_rows": rows if rows is not None else [receipt(1), receipt(2)]}


def receipt(index, **extra):
    return {"id": f"receipt-{index}", "workout_id": "source-session", "exercise_id": "press",
        "workout_occurrence_id": "flex-occurrence", "exercise_occurrence_id": "slot",
        "set_index": index, "set_kind": "work", "parent_set_index": None,
        "created_at": datetime(2026, 10, 28), "performed_date": date(2026, 10, 19 if index == 1 else 27),
        **extra}


def projection(session):
    return [SimpleNamespace(payload={"program_template_id": "authored", "sessions": [session]})]


def test_flexible_multi_day_coverage_is_independent_of_calendar_window():
    session = flexible_session()
    result = calendar_statuses(projection(session), [receipt(2)])
    assert result["2026-10-27"]["status"] == "complete"
    occurrence = result["2026-10-27"]["occurrences"][0]
    assert occurrence["working_sets_completed"] == occurrence["working_sets_planned"] == 2
    assert occurrence["advancement"] == session["advancement"]
    assert occurrence["execution_state"] == "finished"


def test_end_early_and_amended_finish_never_claim_full_completion():
    session = flexible_session("ended_early", [receipt(1)])
    session["advancement"] = {"operation": "end_early", "coverage": [["slot", 1]],
        "missing": [["slot", 2]], "local_day": "2026-10-27"}
    original = deepcopy(session["advancement"])
    result = calendar_statuses(projection(session), [receipt(1)])
    occurrence = result["2026-10-19"]["occurrences"][0]
    assert occurrence["status"] == "ended_early"
    assert result["2026-10-19"]["status"] == "partial"
    assert occurrence["advancement"] == original
    amended = flexible_session("finished", [receipt(1)])
    result = calendar_statuses(projection(amended), [receipt(1)])
    assert result["2026-10-19"]["occurrences"][0]["status"] == "amended_incomplete"
    assert result["2026-10-19"]["occurrences"][0]["advancement"]["missing"] == []


def test_full_coverage_without_finish_remains_active():
    session = flexible_session("active")
    result = calendar_statuses(projection(session), [receipt(1), receipt(2)])
    assert result["2026-10-27"]["occurrences"][0]["status"] == "active"
    assert result["2026-10-27"]["status"] == "partial"


def test_working_coverage_excludes_voids_children_warmups_and_unknown_slots():
    from core_engine.history_status import occurrence_coverage
    session = flexible_session()
    rows = [receipt(1), receipt(2, set_kind="warmup"), receipt(2, parent_set_index=1),
        receipt(2, voided_at=datetime(2026, 10, 29))]
    coverage = occurrence_coverage(session, rows)
    assert coverage["known"] and not coverage["complete"]
    assert coverage["missing"] == [["slot", 2]]
    assert not occurrence_coverage(session, [receipt(1, exercise_occurrence_id="other")])["known"]


def test_flexible_coverage_cannot_accept_duplicate_or_foreign_effective_keys():
    from core_engine.history_status import occurrence_coverage
    session = flexible_session()
    assert not occurrence_coverage(session, [receipt(1), receipt(1, id="duplicate"), receipt(2)])["known"]
    assert not occurrence_coverage(session, [receipt(1, workout_occurrence_id="other-occurrence"), receipt(2)])["known"]


@pytest.fixture
def history_db():
    from app.database import Base
    from app.models import User
    root = Path(os.environ["CI_TEST_ROOT"]).resolve(strict=True)
    target = Path(tempfile.mkdtemp(prefix="history-flexible-", dir=root)) / "history-flexible.sqlite"
    assert target.is_relative_to(root) and not target.exists()
    engine = create_engine(f"sqlite:///{target}")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA database_list").first()[2] == str(target)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid", name="Synthetic history", password_hash="unused", equipment_profile=[])
        db.add(user)
        db.commit()
        yield db, user
    engine.dispose()


def add_occurrence(db, user, *, state="finished", explicit=True, sequence=True):
    from app.models import TrainingSequence, WorkoutOccurrence, WorkoutSetLog
    identity = str(uuid4())
    session = flexible_session(state)
    session["workout_occurrence_id"] = identity
    advancement = session.pop("advancement")
    for key in ("coverage_rows", "actual_dates", "sequence_id", "execution_state"):
        session.pop(key)
    sequence_id = str(uuid4())
    if sequence:
        db.add(TrainingSequence(id=sequence_id, user_id=user.id, program_id="pure_bodybuilding_phase_1_full_body",
            source_digest="0" * 64, source_catalog={}, timezone="America/New_York", consent={}))
        db.flush()
    occurrence = WorkoutOccurrence(id=identity, user_id=user.id, plan_id=None if sequence else "legacy-anchor", week_start=None if sequence else date(2026, 10, 19),
        session_slot=0, scheduled_date=date(2026, 10, 20), workout_id="source-session",
        program_id="pure_bodybuilding_phase_1_full_body", payload=session)
    occurrence.sequence_id = sequence_id if sequence else None
    occurrence.source_position = 0 if sequence else None
    occurrence.execution_state = state if sequence else None
    occurrence.advancement = deepcopy(advancement) if sequence else None
    occurrence.execution_context = {"id": "context-2", "local_day": "2026-10-27", "timezone": "America/New_York"} if sequence else None
    db.add(occurrence)
    db.flush()
    records = []
    for index, day in ((1, date(2026, 10, 19)), (2, date(2026, 10, 27))):
        row = WorkoutSetLog(id=str(uuid4()), user_id=user.id, workout_id="source-session", workout_occurrence_id=identity,
            exercise_occurrence_id="slot", primary_exercise_id="press", exercise_id="press", set_index=index,
            reps=8, weight=10, set_kind="work", created_at=datetime(2026, 10, 28, 3))
        row.performed_local_date = day if explicit else None
        row.performed_timezone = "America/New_York" if explicit else None
        row.execution_context_id = f"context-{index}" if explicit else None
        db.add(row)
        records.append(row)
    db.commit()
    return occurrence, records


def test_explicit_receipt_dates_precede_placement_with_legacy_provenance_retained(history_db):
    from app.history_dates import performed_log_rows
    db, user = history_db
    add_occurrence(db, user)
    rows = performed_log_rows(db, user_id=user.id, start_date=date(2026, 10, 27), end_date=date(2026, 10, 27))
    assert len(rows) == 1
    assert rows[0]["performed_date"] == date(2026, 10, 27)
    assert rows[0]["performed_date_source"] == "explicit_receipt_local_date"
    add_occurrence(db, user, explicit=False, sequence=False)
    legacy = performed_log_rows(db, user_id=user.id, start_date=date(2026, 10, 20), end_date=date(2026, 10, 20))
    assert len(legacy) == 2
    assert {row["performed_date_source"] for row in legacy} == {"legacy_occurrence_scheduled_date"}


def test_history_window_and_day_detail_use_full_effective_occurrence_coverage(history_db):
    from app.routers.history import get_history_calendar, get_history_day_detail
    db, user = history_db
    occurrence, records = add_occurrence(db, user)
    day = date(2026, 10, 27)
    calendar = get_history_calendar(db=db, current_user=user, start_date=day, end_date=day)
    assert calendar["days"][0]["set_count"] == 1
    assert calendar["days"][0]["status"] == "complete"
    detail = get_history_day_detail(day=day, db=db, current_user=user)
    workout = detail["workouts"][0]
    assert workout["title"] == "Source workout"
    assert workout["working_sets_completed"] == workout["working_sets_planned"] == 2
    assert workout["advancement"] == occurrence.advancement
    records[0].voided_at = datetime(2026, 10, 30)
    db.commit()
    amended = get_history_day_detail(day=day, db=db, current_user=user)["workouts"][0]
    assert amended["status"] == "amended_incomplete"
    assert amended["advancement"]["missing"] == []
    assert amended["missing"] == [["slot", 1]]


def test_load_chronology_uses_latest_effective_work_day_and_confirmed_context(history_db):
    from app.workout_load_state import _all_groups, project_authored_load_feedback
    db, user = history_db
    occurrence, records = add_occurrence(db, user, state="active")
    groups = _all_groups(db, user)
    assert groups[0][0][0] == date(2026, 10, 27)
    feedback = project_authored_load_feedback(db, user=user, occurrence=occurrence, exercise=occurrence.payload["exercises"][0])
    assert feedback["next_exposure"]["decision_trace"]["history_scope"]["cutoff_date"] == "2026-10-27"
    assert feedback["next_exposure"]["decision_trace"]["history_scope"]["cutoff_source"] == "confirmed_execution_context_local_day"
    records[1].voided_at = datetime(2026, 10, 30)
    db.commit()
    assert _all_groups(db, user)[0][0][0] == date(2026, 10, 19)


def test_flexible_detail_receipts_disclose_actual_date_and_audit_date(history_db):
    from app.routers.history import get_history_day_detail
    db, user = history_db
    add_occurrence(db, user)
    detail = get_history_day_detail(day=date(2026, 10, 27), db=db, current_user=user)
    row = detail["workouts"][0]["exercises"][0]["sets"][0]
    assert row["performed_date"] == "2026-10-27"
    assert row["performed_timezone"] == "America/New_York"
    assert row["performed_date_source"] == "explicit_receipt_local_date"
    assert row["created_at"] == "2026-10-28T03:00:00"


def test_finish_acknowledgment_day_is_distinct_from_actual_work(history_db):
    from app.routers.history import get_history_day_detail
    db, user = history_db
    occurrence, _ = add_occurrence(db, user)
    occurrence.advancement = {**occurrence.advancement, "local_day": "2026-10-30"}
    db.commit()
    detail = get_history_day_detail(day=date(2026, 10, 30), db=db, current_user=user)
    workout = detail["workouts"][0]
    assert detail["totals"]["set_count"] == 0
    assert workout["actual_dates"] == ["2026-10-19", "2026-10-27"]
    assert workout["date_role"] == "advancement"
    assert workout["advancement"]["local_day"] == "2026-10-30"
