"""Real PostgreSQL lock and history qualification using the guarded M2B fixture."""
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from test_selected_date_postgres import pg_scenario, _dates, _post, _monday, target
from app import selected_date_plans
from app.database import SessionLocal
from app.models import AuthoredLoadState, WorkoutLogCommand, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog


def _next_dates(offsets=(0,3,5), revision=0):
    request = _dates(offsets, revision)
    request['week_start'] = (_monday()+timedelta(days=7)).isoformat()
    request['selected_dates'] = [( date.fromisoformat(day)+timedelta(days=7)).isoformat() for day in request['selected_dates']]
    return request


def test_future_same_revision_has_one_winner_and_leaves_current_history(pg_scenario, monkeypatch):
    user_id, headers, current = pg_scenario
    session = current['sessions'][0]
    exercise = session['exercises'][0]
    log = _post(headers, f"/workout/{session['workout_occurrence_id']}/log-set", {
        'command_id':uuid4().hex, 'exercise_id':exercise['id'],
        'exercise_occurrence_id':exercise['exercise_occurrence_id'],'set_index':1,'reps':8,'weight':25})
    assert log.status_code == 200, log.text
    def records(db, model):
        return {r.id:{c.key:deepcopy(getattr(r,c.key)) for c in model.__table__.columns}
            for r in db.query(model).filter_by(user_id=user_id)}
    with SessionLocal() as db:
        before = deepcopy(db.query(WorkoutPlan).filter_by(user_id=user_id).one().payload)
        frozen = deepcopy(db.query(WorkoutOccurrence).filter_by(user_id=user_id).one().payload)
        evidence = [(r.id,r.created_at,r.weight) for r in db.query(WorkoutSetLog).filter_by(user_id=user_id)]
        retained = {model:records(db,model) for model in (WorkoutSetLog,WorkoutLogCommand,AuthoredLoadState)}
        assert retained[WorkoutSetLog] and retained[WorkoutLogCommand]
    request = _next_dates()
    preview = _post(headers, '/plan/selected-dates/preview', request)
    assert preview.status_code == 200, preview.text
    barrier=Barrier(2)
    original = selected_date_plans.lock_history_user
    def race(db, uid):
        barrier.wait(timeout=15)
        return original(db,uid)
    monkeypatch.setattr(selected_date_plans,'lock_history_user',race)
    payload={**request,'expected_preview_digest':preview.json()['schedule']['preview_digest']}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _: _post(headers,'/plan/generate-week',payload),range(2)))
    assert sorted(r.status_code for r in responses)==[200,409]
    winner=next(r.json() for r in responses if r.status_code==200)
    assert winner['mesocycle']['authored_week_index']==2
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count()==2
        assert db.query(WorkoutPlan).filter_by(user_id=user_id,week_start=_monday()).one().payload==before
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).one().payload==frozen
        assert [(r.id,r.created_at,r.weight) for r in db.query(WorkoutSetLog).filter_by(user_id=user_id)]==evidence
        assert {model:records(db,model) for model in retained} == retained
