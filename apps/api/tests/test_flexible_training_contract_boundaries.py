"""Legacy date-contract boundaries motivating the separately approved sequence design.

These are characterizations, not proof that flexible execution is implemented.
Only explicit disposable SQLite fixtures are imported; no production target.
"""
from copy import deepcopy
from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.database import SessionLocal
from app.history_dates import performed_log_rows
from app.models import WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.program_loader import load_program_template
from app.selected_date_plans import resolve_source_successor
from app.workout_identity import identified_sessions
from core_engine.history_status import calendar_statuses
from core_engine.selected_date_scheduler import validate_selected_week
from app.routers import workout
from test_selected_date_scheduling import scenario  # fixture dependency, explicit disposable target
from test_next_planned_workout import planned, preview, stored


def freeze_today(monkeypatch, day):
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            instant=datetime.combine(day,datetime.min.time(),UTC).replace(hour=16)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(workout,'datetime',Clock)


def snapshot(db,uid,pid,slot=0):
    row=db.get(WorkoutPlan,pid);session=identified_sessions(row)[slot]
    occurrence=WorkoutOccurrence(id=session['workout_occurrence_id'],user_id=uid,plan_id=pid,
        week_start=row.week_start,session_slot=slot,workout_id=session['session_id'],
        program_id=row.payload['program_template_id'],payload=session,
        scheduled_date=date.fromisoformat(session['scheduled_date']),schedule_timezone='America/New_York',placement_revision=1)
    db.add(occurrence);db.flush()
    return occurrence,session


def log(db,uid,occurrence,session,index,created_at):
    exercise=session['exercises'][0]
    db.add(WorkoutSetLog(user_id=uid,workout_id=session['session_id'],workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise['exercise_occurrence_id'],primary_exercise_id=exercise['id'],exercise_id=exercise['id'],
        set_index=index,reps=8,weight=20,set_kind='work',created_at=created_at))


def test_missed_date_retains_identity_work_and_unstarted_state(planned,monkeypatch):
    uid,headers,client,pid=planned;before=stored(pid)
    freeze_today(monkeypatch,date(2026,10,28))
    assert client.get('/workout/today',headers=headers).status_code==404
    value=preview(client,headers)
    assert value['original_date']=='2026-10-27'
    assert value['session']['exercises'][0]['source_lineage']['source_slot_id']=='source-0'
    assert stored(pid)==before
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count()==1
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count()==0
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count()==0


def test_completed_earlier_work_still_freezes_legacy_week(planned,monkeypatch):
    uid,headers,client,pid=planned;before=stored(pid)
    with SessionLocal() as db:
        occurrence,session=snapshot(db,uid,pid)
        for index in (1,2):log(db,uid,occurrence,session,index,datetime(2026,10,27,17))
        db.commit();identified=identified_sessions(db.get(WorkoutPlan,pid))
        rows=performed_log_rows(db,user_id=uid)
        status=calendar_statuses([SimpleNamespace(payload={**before,'sessions':identified})],rows)
        assert status['2026-10-27']['occurrences'][0]['status']=='complete'
    freeze_today(monkeypatch,date(2026,10,28))
    value=preview(client,headers)
    assert value['original_date']=='2026-10-29' and not value['can_move']
    assert 'snapshot' in value['blocked_reason']
    assert stored(pid)==before
    with SessionLocal() as db:assert db.query(WorkoutSetLog).filter_by(user_id=uid).count()==2


def test_monday_rollover_keeps_outstanding_work_but_cannot_start_it(planned,monkeypatch):
    uid,headers,client,pid=planned;before=stored(pid)
    freeze_today(monkeypatch,date(2026,11,2))
    assert client.get('/workout/today',headers=headers).status_code==404
    value=preview(client,headers)
    assert value['original_date']=='2026-10-27' and not value['can_move']
    assert 'across local weeks' in value['blocked_reason']
    assert stored(pid)==before
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count()==1
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count()==0


def test_consent_snapshot_is_not_evidence_of_actual_completion(planned):
    uid,headers,client,pid=planned
    with SessionLocal() as db:
        snapshot(db,uid,pid);db.commit();row=db.get(WorkoutPlan,pid)
        status=calendar_statuses([SimpleNamespace(payload={**row.payload,'sessions':identified_sessions(row)})],[])
        assert status['2026-10-27']['occurrences'][0]['status']=='scheduled'
        assert status['2026-10-27']['occurrences'][0]['working_sets_completed']==0
    # The legacy occupied-slot selector excludes snapshots; a new completion
    # selector must not mistake this old filter for a progression decision.
    assert preview(client,headers)['original_date']=='2026-10-29'


def test_legacy_performed_date_is_frozen_placement_not_new_execution_day(planned):
    uid,_,_,pid=planned
    with SessionLocal() as db:
        occurrence,session=snapshot(db,uid,pid)
        log(db,uid,occurrence,session,1,datetime(2026,10,28,17));db.commit()
        receipt=performed_log_rows(db,user_id=uid)[0]
        assert receipt['created_at'].date()==date(2026,10,28)
        assert receipt['performed_date']==date(2026,10,27)
        assert db.get(WorkoutOccurrence,occurrence.id).scheduled_date==date(2026,10,27)


def test_calendar_reservation_successor_is_not_a_completion_cursor(planned):
    uid,_,_,pid=planned;program='pure_bodybuilding_phase_1_full_body'
    # Use admitted compiled source lineage to pass the existing successor guard.
    source=deepcopy(load_program_template(program)['authored_weeks'][0])
    source.update(program_template_id=program,mesocycle={'authored_week_index':1},
        schedule={'mode':'selected_dates_v1'})
    with SessionLocal() as db:
        row=db.get(WorkoutPlan,pid);row.payload=source;db.commit()
        selected=validate_selected_week(week_start=date(2026,11,2),selected_dates=[date(2026,11,3),date(2026,11,5)],
            timezone='America/New_York',planning_instant=datetime(2026,10,28,16,tzinfo=UTC))
        ordinal,dependency=resolve_source_successor([row],selected,program)
        assert ordinal==2 and dependency['predecessor_plan_id']==row.id
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count()==0
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count()==0
