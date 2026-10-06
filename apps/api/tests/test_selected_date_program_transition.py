"""Current-week program transitions on verified disposable targets only."""
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

explicit = os.environ.get('TEST_DATABASE_URL')
assert explicit and os.environ.get('DATABASE_URL') == explicit
target = make_url(explicit)
if target.get_backend_name() == 'postgresql':
    assert os.environ.get('M2B_POSTGRES_ISOLATED') == '1'
    assert (target.drivername, target.host, target.port, target.database, target.username) == (
        'postgresql+psycopg', '127.0.0.1', 25461, 'm2b_qualification', 'm2b_test')
    probe = create_engine(target)
    with probe.connect() as db:
        assert tuple(db.execute(text('SELECT current_database(),current_user,inet_server_port()')).one()) == (
            'm2b_qualification', 'm2b_test', 5432)
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0021_selected_workout_dates'
    probe.dispose()
else:
    root = Path(os.environ['HIST_TEST_ROOT']).resolve(strict=True)
    assert target.get_backend_name() == 'sqlite' and target.database not in (None, ':memory:')
    database = Path(target.database).resolve()
    assert root != Path('/') and database.is_relative_to(root)
    with sqlite3.connect(database) as db:
        identity = db.execute('PRAGMA database_list').fetchall()
        assert len(identity) == 1 and Path(identity[0][2]).resolve() == database

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.routers import plan as plan_router
from app import selected_date_plans
from app.security import create_access_token

PH1 = 'pure_bodybuilding_phase_1_full_body'
PH2 = 'pure_bodybuilding_phase_2_full_body'
PREVIEW = '/plan/selected-dates/preview'
ACTIVATE = '/plan/generate-week'


@pytest.fixture
def scenario(monkeypatch):
    assert engine.url == target
    if engine.dialect.name == 'sqlite':
        Base.metadata.create_all(engine)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2026, 10, 6, 16, tzinfo=UTC)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(plan_router, 'datetime', Clock)
    monkeypatch.setattr(selected_date_plans, 'datetime', Clock)
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f'{uuid4()}@example.invalid', name='Synthetic program transition',
            password_hash='not-a-login', selected_program_id=PH1, split_preference='full_body',
            days_available=5, equipment_profile=['dumbbell','barbell','bench','cable','machine'],
            nutrition_phase='maintenance'))
        db.commit()
    client = TestClient(app)
    yield user_id, {'Authorization': f'Bearer {create_access_token(user_id)}'}, client
    client.close()


def request(program=PH1):
    return {'template_id': program, 'week_start': '2026-10-05', 'timezone': 'America/New_York',
        'selected_dates': ['2026-10-06','2026-10-09','2026-10-11'], 'target_days': 3,
        'expected_placement_revision': 0}


def seed_plan(user_id, program, *, superseded=False):
    payload = {'program_template_id': program, 'split': 'full_body', 'phase': 'accumulation',
        'mesocycle': {'authored_week_index': 4, 'week_index': 4}, 'sessions': [
            {'session_id': f'saved-source-{index}', 'day_role': 'full_body', 'exercises': [
                {'id': 'bench_press', 'name': 'Bench press', 'sets': index+1, 'rep_range': [8,10],
                 'recommended_working_weight': 77.5+index,
                 'source_lineage': {'source_slot_id': f'protected-slot-{index}'}}]}
            for index in range(3)]}
    if superseded:
        payload['schedule'] = {'mode': 'selected_dates_superseded_v1'}
    with SessionLocal() as db:
        row = WorkoutPlan(user_id=user_id, week_start=date(2026,10,5), split='full_body',
            phase='accumulation', payload=payload)
        db.add(row)
        db.commit()
        return row.id, deepcopy(payload)


def snapshot(user_id):
    with SessionLocal() as db:
        result = {}
        for model in [User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog]:
            key = 'id' if model is User else 'user_id'
            rows = db.query(model).filter(getattr(model,key) == user_id).order_by(model.id).all()
            result[model.__tablename__] = [{c.key: deepcopy(getattr(row,c.key))
                for c in model.__table__.columns} for row in rows]
        return result


def assert_transition_rejected(client, headers, path, payload):
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code == 409, response.text
    assert 'transition' in response.json()['detail'].lower() or 'reconcil' in response.json()['detail'].lower()


@pytest.mark.parametrize('path', [PREVIEW, ACTIVATE])
@pytest.mark.parametrize('choice', ['explicit', 'saved'])
def test_other_legacy_program_requires_transition_without_writes(scenario, path, choice):
    user_id, headers, client = scenario
    seed_plan(user_id, PH1)
    payload = request(PH2)
    if choice == 'saved':
        with SessionLocal() as db:
            db.get(User,user_id).selected_program_id = PH2
            db.commit()
        payload['template_id'] = None
    before = snapshot(user_id)
    assert_transition_rejected(client,headers,path,payload)
    assert snapshot(user_id) == before


def test_other_undated_plan_inserted_after_preview_blocks_activation_without_writes(scenario):
    user_id, headers, client = scenario
    payload = request(PH2)
    preview = client.post(PREVIEW,headers=headers,json=payload)
    assert preview.status_code == 200, preview.text
    payload['expected_preview_digest'] = preview.json()['schedule']['preview_digest']
    seed_plan(user_id,PH1)
    before = snapshot(user_id)
    assert_transition_rejected(client,headers,ACTIVATE,payload)
    assert snapshot(user_id) == before


@pytest.mark.parametrize('path', [PREVIEW, ACTIVATE])
def test_unknown_auto_preserves_existing_program_and_source_without_generation(scenario, monkeypatch, path):
    user_id, headers, client = scenario
    plan_id, saved = seed_plan(user_id,PH1)
    with SessionLocal() as db:
        user = db.get(User,user_id)
        user.selected_program_id, user.program_selection_mode = None, 'auto'
        db.commit()
    def displaced_auto_choice(**kwargs):
        pytest.fail('Existing current-week work must be placed without invoking Auto to choose another program')
    monkeypatch.setattr(plan_router,'_build_week_plan_runtime_for_user',displaced_auto_choice)
    before = snapshot(user_id)
    response = client.post(path,headers=headers,json=request(None))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['program_template_id'] == PH1 and result['mesocycle'] == saved['mesocycle']
    for old,new in zip(saved['sessions'],result['sessions']):
        assert old['session_id'] == new['session_id']
        assert old['exercises'] == [{k:v for k,v in e.items()
            if k not in ['exercise_occurrence_id','execution_slot']} for e in new['exercises']]
    if path == PREVIEW:
        assert snapshot(user_id) == before
    else:
        with SessionLocal() as db:
            assert db.query(WorkoutPlan).filter_by(user_id=user_id).one().id == plan_id
            assert db.get(User,user_id).program_selection_mode == 'auto'
            assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 0
            assert db.query(WorkoutSetLog).filter_by(user_id=user_id).count() == 0


@pytest.mark.parametrize('path', [PREVIEW, ACTIVATE])
def test_unknown_auto_cannot_select_over_conflicting_current_programs(scenario, monkeypatch, path):
    user_id, headers, client = scenario
    seed_plan(user_id,PH1)
    seed_plan(user_id,PH2)
    with SessionLocal() as db:
        user = db.get(User,user_id)
        user.selected_program_id, user.program_selection_mode = None, 'auto'
        db.commit()
    def generate_different_program(**kwargs):
        pytest.fail('Ambiguous current-week programs must require reconciliation before Auto generation')
    monkeypatch.setattr(plan_router,'_build_week_plan_runtime_for_user',generate_different_program)
    before = snapshot(user_id)
    assert_transition_rejected(client,headers,path,request(None))
    assert snapshot(user_id) == before


@pytest.mark.parametrize('path', [PREVIEW, ACTIVATE])
def test_superseded_other_program_does_not_block_current_saved_work(scenario, monkeypatch, path):
    user_id, headers, client = scenario
    _, saved = seed_plan(user_id,PH1)
    superseded_id, superseded = seed_plan(user_id,PH2,superseded=True)
    before = snapshot(user_id)
    def regenerate(**kwargs):
        pytest.fail('A matching saved plan must preserve source prescriptions')
    monkeypatch.setattr(plan_router,'_build_week_plan_runtime_for_user',regenerate)
    response = client.post(path,headers=headers,json=request(PH1))
    assert response.status_code == 200, response.text
    assert response.json()['mesocycle'] == saved['mesocycle']
    with SessionLocal() as db:
        assert db.get(WorkoutPlan,superseded_id).payload == superseded
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 2
    if path == PREVIEW:
        assert snapshot(user_id) == before
