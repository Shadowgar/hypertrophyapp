"""Opt-in actual PostgreSQL move serialization; explicit disposable target only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event
from uuid import uuid4
import os
import pytest

if os.environ.get('M2B_CURRENT_POSTGRES_ISOLATED') != '1':
    pytest.skip('Requires verified disposable current-schema PostgreSQL', allow_module_level=True)
from postgres_qualification_target import selected_date_target
from sqlalchemy import create_engine, text
url=os.environ['TEST_DATABASE_URL'];expected=selected_date_target(url,os.environ)
probe=create_engine(url)
with probe.connect() as connection:
    assert tuple(connection.execute(text('SELECT current_database(),current_user')).one()) == (expected.database, expected.user)
    assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()==expected.revision
probe.dispose()

from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog
from app.routers import plan,workout
from app import selected_date_plans, next_planned_workout
from auth_test_helpers import create_access_token


@pytest.fixture
def pg_next(monkeypatch):
    monday=datetime.now(UTC).date();monday-=timedelta(days=monday.weekday())
    instant=datetime.combine(monday,datetime.min.time(),UTC)+timedelta(hours=16)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant
    for module in (plan,workout,selected_date_plans):monkeypatch.setattr(module,'datetime',Clock)
    uid=str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=uid,email=uid+'@example.invalid',name='Synthetic PostgreSQL schedule',password_hash='unused',split_preference='full_body',
            selected_program_id='pure_bodybuilding_phase_1_full_body',days_available=3,
            equipment_profile=['dumbbell','barbell','bench','cable','machine'],nutrition_phase='maintenance'))
        db.commit()
    headers={'Authorization':'Bearer '+create_access_token(uid)}
    client=TestClient(app)
    response=client.post('/plan/generate-week',headers=headers,json={'template_id':'pure_bodybuilding_phase_1_full_body',
        'week_start':str(monday),'selected_dates':[str(monday+timedelta(days=i)) for i in (1,3,5)],
        'timezone':'America/New_York','expected_placement_revision':0,'target_days':3})
    assert response.status_code==200,response.text
    initial=response.json();value=client.get('/workout/next-planned',headers=headers).json();assert value['can_move']
    body={'plan_id':value['plan_id'],'workout_occurrence_id':value['workout_occurrence_id'],
        'expected_original_date':value['original_date'],'expected_local_today':value['local_today'],
        'expected_placement_revision':value['placement_revision'],'expected_preview_digest':value['preview_digest'],'confirmed':True}
    return uid,headers,initial,body


def post(headers,path,body):
    c=TestClient(app)
    try:return c.post(path,headers=headers,json=body)
    finally:c.close()


def test_two_confirmations_serialize_to_one_move(pg_next):
    uid,headers,initial,body=pg_next;barrier=Barrier(2)
    def move():
        barrier.wait(timeout=10);return post(headers,'/workout/next-planned/move',body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(move),pool.submit(move)]]
    assert sorted(r.status_code for r in results)==[200,409]
    moved=next(r.json() for r in results if r.status_code==200)
    assert [s['workout_occurrence_id'] for s in moved['sessions']]==[s['workout_occurrence_id'] for s in initial['sessions']]
    assert [s['exercises'] for s in moved['sessions']]==[s['exercises'] for s in initial['sessions']]
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count()==1
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count()==0


def test_started_work_wins_user_lock_and_move_is_refused(pg_next,monkeypatch):
    uid,headers,initial,body=pg_next
    start_locked=Event();release=Event();move_requested=Event()
    original_start=workout._lock_history_user;original_move=next_planned_workout.lock_history_user
    def starting(db,user_id):
        original_start(db,user_id);start_locked.set();assert release.wait(15)
    def moving(db,user_id):
        move_requested.set();original_move(db,user_id)
    monkeypatch.setattr(workout,'_lock_history_user',starting)
    monkeypatch.setattr(next_planned_workout,'lock_history_user',moving)
    first=initial['sessions'][0];exercise=first['exercises'][0]
    log={'command_id':str(uuid4()),'exercise_id':exercise['id'],'exercise_occurrence_id':exercise['exercise_occurrence_id'],
        'set_index':1,'reps':8,'weight':25}
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(post,headers,f"/workout/{first['workout_occurrence_id']}/log-set",log)
        assert start_locked.wait(15)
        b=pool.submit(post,headers,'/workout/next-planned/move',body)
        assert move_requested.wait(15);release.set()
        started=a.result(timeout=30);moved=b.result(timeout=30)
    assert started.status_code==200,started.text
    assert moved.status_code==409,moved.text
    with SessionLocal() as db:
        row=db.query(WorkoutPlan).filter_by(user_id=uid).one();assert row.placement_revision==1
        occurrence=db.get(WorkoutOccurrence,first['workout_occurrence_id'])
        assert str(occurrence.scheduled_date)==first['scheduled_date']
        assert db.query(WorkoutSetLog).filter_by(user_id=uid,workout_occurrence_id=occurrence.id).count()==1
