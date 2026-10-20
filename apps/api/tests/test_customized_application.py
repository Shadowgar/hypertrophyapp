"""Real registered application routes on the explicitly owned PostgreSQL target."""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def application(monkeypatch):
    manifest = os.environ.get('C3B2B_TARGET_MANIFEST')
    if not manifest:
        pytest.skip('Explicit disposable PostgreSQL manifest required')
    from research.m4c3b2b.target import open_target
    pg = open_target(manifest)
    from app.main import app
    from app.database import Base, get_db
    from app.config import settings
    # Only the verified disposable table copies; never reset existing tables.
    with pg.begin() as conn:
        for table in Base.metadata.sorted_tables:
            table.create(conn, checkfirst=True)
    Session = sessionmaker(bind=pg)
    def db():
        with Session() as session:
            yield session
    app.dependency_overrides[get_db] = db
    monkeypatch.setattr(settings, 'customized_enabled', True)
    import app.main as main
    monkeypatch.setattr(main, 'customized_clock', lambda: datetime(2026, 10, 19, 12, tzinfo=UTC), raising=False)
    # Today and #83 own their explicit server instant too; keep this synthetic
    # journey coherent as the host calendar advances (including DST boundaries).
    class FixedDatetime(datetime):
        @classmethod
        def now(cls,tz=None):
            instant=main.customized_clock()
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    import app.routers.workout as workout
    import app.routers.plan as plan
    monkeypatch.setattr(workout,'datetime',FixedDatetime)
    monkeypatch.setattr(plan,'datetime',FixedDatetime)
    client = TestClient(app)
    account = {'email': f'{uuid4().hex}@example.com', 'name': 'Synthetic M4', 'password': 'Synthetic-only-safe-123!'}
    r = client.post('/auth/register', json=account)
    assert r.status_code == 200, r.text
    headers = {'Authorization': 'Bearer '+r.json()['access_token']}
    yield client, headers, Session, account
    app.dependency_overrides.clear()
    client.close()
    pg.dispose()


def request(**changes):
    return dict(mode='customized', bundle_id='shorter-current', goal='hypertrophy',
        training_context='current', population='broadly_healthy_adult', selected_dates=['2026-10-19','2026-10-21','2026-10-23'],
        timezone='America/New_York', cap_minutes=60, cap_kind='hard',
        equipment=['machine','floor','dumbbell','bench','bodyweight','leg_press_station','chest_press_station',
            'row_station','leg_curl_station','pulldown_station','calf_station'], skill='intermediate', restrictions=[], **changes)


def post(c,h,path,data,key=None):
    return c.post(path, headers={**h,'Idempotency-Key':key or uuid4().hex}, json=data)


def accepted(app, body=None):
    c,h,_,_=app
    p=post(c,h,'/customized/proposals',body or request())
    assert p.status_code==200,p.text
    p=p.json()
    ch=post(c,h,f"/customized/proposals/{p['proposal_id']}/challenge",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert ch.status_code==200,(ch.text,p['blocking_reasons'],p['snapshot']['preview']['reasons'],[(s['cap_status'],s['maximum_minutes']) for s in p['snapshot']['preview']['sessions']])
    ch=ch.json()
    a=post(c,h,f"/customized/proposals/{p['proposal_id']}/accept",dict(protocol='compact-candidate-consent-v2',
        expected_revision=ch['revision'],snapshot_hash=ch['snapshot_hash'],challenge=ch['challenge'],terms_hash=ch['terms_hash'],
        summary_hash=ch['summary_hash'],mode='customized',agree=True))
    assert a.status_code==200,a.text
    return a.json()


def test_real_workflow_publish_today_log_correct_complete_history(application):
    c,h,Session,_=application
    a=accepted(application)
    assert a['snapshot']['preview']['sessions'][0]['maximum_minutes']<=60
    assert a['snapshot']['authority']['policy']=='provisional'
    assert not a['snapshot']['authority']['source_verified']
    path=f"/customized/proposals/{a['proposal_id']}/activate"
    payload=dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash'])
    r=post(c,h,path,payload,'activate-once')
    assert r.status_code==200,r.text
    assert post(c,h,path,payload,'activate-once').json()==r.json()
    t=c.get('/workout/today',headers=h)
    assert t.status_code==200,t.text
    t=t.json()
    assert t['program_template_id']=='customized_full_body_v1'
    assert sum(e['sets'] for e in t['exercises'])==11
    e=t['exercises'][0];wid=t['workout_occurrence_id']
    log=post(c,h,f'/workout/{wid}/log-set',dict(command_id='first',exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10))
    assert log.status_code==200,log.text
    assert c.get(f'/workout/{wid}/progress',headers=h).json()['completed_total']==1
    # Same existing correction endpoint; no parallel Customized log store.
    from app.models import WorkoutSetLog,WorkoutPlan
    with Session() as db:
        receipt=db.query(WorkoutSetLog).filter_by(workout_occurrence_id=wid).one()
        record_id=receipt.id
        assert db.query(WorkoutPlan).filter_by(id=r.json()['active_plan_id']).one().payload['customized']['consent_receipt']
    correction=post(c,h,f'/workout/set/{record_id}/correct',dict(command_id='correct-first',reps=9,weight=12,reason='Synthetic correction'))
    assert correction.status_code==200,correction.text
    for exercise in t['exercises']:
        for index in range(1,exercise['sets']+1):
            if exercise is e and index==1:continue
            result=post(c,h,f'/workout/{wid}/log-set',dict(command_id=uuid4().hex,exercise_id=exercise['id'],exercise_occurrence_id=exercise['exercise_occurrence_id'],set_index=index,reps=10,weight=0 if exercise['id']=='floor_crunch' else 10))
            assert result.status_code==200,result.text
    progress=c.get(f'/workout/{wid}/progress',headers=h)
    assert progress.json()['percent_complete']==100,progress.text
    history=c.get('/history/calendar?start_date=2026-10-19&end_date=2026-10-25',headers=h)
    assert history.status_code==200,history.text
    with Session() as db:
        assert db.query(WorkoutSetLog).filter_by(workout_occurrence_id=wid).count()==12


def test_cross_account_and_reset_cannot_use_proposal(application):
    c,h,_,account=application
    a=accepted(application)
    other=c.post('/auth/register',json={**account,'email':uuid4().hex+'@example.com'}).json()
    foreign={'Authorization':'Bearer '+other['access_token']}
    assert c.get(f"/customized/proposals/{a['proposal_id']}",headers=foreign).status_code==404
    c.post('/customized/session/revoke',headers=h)
    assert post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash'])).status_code==401


def test_revision_invalidates_consent_and_active_snapshot_is_immutable(application):
    c,h,Session,_=application
    a=accepted(application)
    revised=post(c,h,f"/customized/proposals/{a['proposal_id']}/revisions",dict(expected_revision=a['revision'],request=request()))
    assert revised.status_code==200,revised.text
    p=revised.json()
    assert p['consent_receipt'] is None and p['plan_version']==2
    stale=post(c,h,f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert stale.status_code==409
    a=accepted(application)
    active=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash'])).json()
    for action,body in [('revisions',dict(expected_revision=active['revision'],request=request())),('withdraw',dict(expected_revision=active['revision']))]:
        response=post(c,h,f"/customized/proposals/{a['proposal_id']}/{action}",body)
        assert response.status_code==409,response.text


@pytest.mark.parametrize('change',[
    {'selected_dates':['2026-10-19','2026-10-20','2026-10-23']},
    {'selected_dates':['2026-10-19','2026-10-21','2026-10-21']},
    {'equipment':['dumbbell','floor']},
    {'training_context':'unknown'},
    {'restrictions':['avoid_horizontal_press']},
    {'cap_minutes':20},
])
def test_incomplete_infeasible_inputs_cannot_be_accepted(application,change):
    c,h,_,_=application
    body=request();body.update(change)
    r=post(c,h,'/customized/proposals',body)
    if r.status_code==200:
        p=r.json()
        response=post(c,h,f"/customized/proposals/{p['proposal_id']}/challenge",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
        assert response.status_code in (409,422),response.text
    else:assert r.status_code==422,r.text


@pytest.mark.parametrize('status',['new','returning'])
def test_training_status_and_future_dates_use_same_original_planner(application,status):
    c,h,Session,_=application
    body=request();body.update(bundle_id='longer-'+status,training_context=status,
        selected_dates=['2026-10-26','2026-10-28','2026-10-30'])
    a=accepted(application,body)
    first=a['snapshot']['preview']['sessions'][0]
    assert first['exercises'][0]['target_min']==3
    assert first['exercises'][0]['target_max']==4
    active=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert active.status_code==200,active.text
    assert c.get('/workout/today',headers=h).status_code==404


def test_two_concurrent_activations_have_one_winner(application):
    from concurrent.futures import ThreadPoolExecutor
    c,h,Session,_=application
    a,b=accepted(application),accepted(application)
    def activate(p):
        return post(c,h,f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(activate,[a,b]))
    assert sorted(r.status_code for r in results)==[200,409]
    from app.models import WorkoutPlan
    with Session() as db:assert db.query(WorkoutPlan).filter_by(id=next(r for r in results if r.status_code==200).json()['active_plan_id']).count()==1


def test_credential_change_rejects_existing_new_session_tokens(application):
    c,h,Session,account=application
    a=accepted(application)
    from app.models import User
    from app.security import hash_password
    with Session() as db:
        user=db.query(User).filter_by(email=account['email']).one()
        user.password_hash=hash_password('Replacement-synthetic-123!');db.commit()
    denied=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert denied.status_code==401,denied.text
    assert c.get('/workout/today',headers=h).status_code==401


def test_customized_summary_and_undo_do_not_infer_progression(application):
    c,h,_,_=application
    a=accepted(application)
    r=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert r.status_code==200,r.text
    t=c.get('/workout/today',headers=h).json();e=t['exercises'][0];wid=t['workout_occurrence_id']
    r=post(c,h,f'/workout/{wid}/log-set',dict(command_id='receipt',exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=10,weight=15))
    assert r.status_code==200,r.text
    summary=c.get(f'/workout/{wid}/summary',headers=h)
    assert summary.status_code==200,summary.text
    assert all(x['next_working_weight'] is None for x in summary.json()['exercises']),summary.text
    undone=post(c,h,f'/workout/{wid}/undo-last-set',dict(command_id='undo',exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id']))
    assert undone.status_code==200,undone.text
    assert c.get(f'/workout/{wid}/progress',headers=h).json()['completed_total']==0
    assert c.get('/workout/today',headers=h).json()['exercises'][0]['recommended_working_weight'] is None


def test_shared_scheduler_cannot_change_accepted_program_dates_without_new_consent(application):
    c,h,_,_=application
    a=accepted(application)
    r=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert r.status_code==200,r.text
    from app.models import User
    from app.security import jwt
    claims=jwt.decode(h['Authorization'][7:],options={'verify_signature':False})
    with application[2]() as db:
        user=db.get(User,claims['sub']);user.split_preference='full_body';user.days_available=3;db.commit()
    changed=post(c,h,'/plan/selected-dates/preview',dict(template_id='customized_full_body_v1',selected_dates=['2026-10-20','2026-10-22','2026-10-24'],week_start='2026-10-19',timezone='America/New_York',expected_placement_revision=1))
    assert changed.status_code==409,changed.text


def test_additive_migration_on_disposable_source_copies_preserves_records(application):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.models import User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState
    engine=application[2].kw['bind']
    schema='m4_migration_'+uuid4().hex
    with engine.begin() as conn:
        conn.execute(text('CREATE SCHEMA '+schema))
        conn.execute(text('SET LOCAL search_path TO '+schema))
        for model in (User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState):
            model.__table__.create(conn)
        conn.execute(text("INSERT INTO users(id,email,password_hash,name,created_at) VALUES ('retained','retained@example.com','synthetic','Retained source',CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO workout_plans(id,user_id,week_start,split,phase,payload,created_at) VALUES ('retained-plan','retained','2026-10-12','full_body','authored',CAST(:payload AS json),CURRENT_TIMESTAMP)"),dict(payload='{\"retained\":true}'))
        before=conn.execute(text('SELECT id,user_id,payload::text FROM workout_plans')).all()
        spec=importlib.util.spec_from_file_location('migration',Path(__file__).parents[1]/'alembic/versions/0022_customized_application.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()
        assert conn.execute(text('SELECT id,user_id,payload::text FROM workout_plans')).all()==before
        assert conn.execute(text('SELECT count(*) FROM customized_candidate_events')).scalar()==0
        assert conn.execute(text('SELECT version FROM customized_candidate_schema')).scalar()==1
        assert conn.execute(text('SELECT count(*) FROM pg_indexes WHERE schemaname=:s'),dict(s=schema)).scalar()>=11


def test_future_customized_activation_preserves_existing_authored_plan_and_receipts(application):
    from copy import deepcopy
    from app.models import User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog
    from app.workout_identity import identified_sessions
    c,h,Session,account=application
    with Session() as db:
        user=db.query(User).filter_by(email=account['email']).one()
        payload=dict(program_template_id='pure_bodybuilding_phase_1_full_body',sessions=[dict(session_id='retained-authored-'+str(i),
            title='Synthetic retained Authored slot',scheduled_date=d,schedule_timezone='America/New_York',placement_revision=1,
            exercises=[dict(id='retained-slot',name='Synthetic retained source',sets=2,rep_range=[8,12])])
            for i,d in enumerate(['2026-10-19','2026-10-21','2026-10-23'])],
            schedule=dict(mode='selected_dates_v1',week_start='2026-10-19',timezone='America/New_York',selected_dates=['2026-10-19','2026-10-21','2026-10-23'],placement_revision=1))
        plan=WorkoutPlan(user_id=user.id,week_start=datetime(2026,10,19).date(),schedule_timezone='America/New_York',placement_revision=1,split='full_body',phase='authored',payload=payload)
        db.add(plan);db.flush()
        session=identified_sessions(plan)[0]
        occurrence=WorkoutOccurrence(id=session['workout_occurrence_id'],user_id=user.id,plan_id=plan.id,
            week_start=plan.week_start,scheduled_date=plan.week_start,schedule_timezone=plan.schedule_timezone,placement_revision=1,
            session_slot=0,workout_id=session['session_id'],program_id=payload['program_template_id'],payload=session)
        db.add(occurrence);db.flush()
        receipt=WorkoutSetLog(user_id=user.id,workout_id=occurrence.workout_id,workout_occurrence_id=occurrence.id,
            exercise_occurrence_id=session['exercises'][0]['exercise_occurrence_id'],primary_exercise_id='retained-slot',exercise_id='retained-slot',set_index=1,reps=9,weight=12,rpe=None)
        db.add(receipt);db.commit()
        pid=plan.id;rid=receipt.id;before=deepcopy(plan.payload)
    body=request();body['selected_dates']=['2026-10-26','2026-10-28','2026-10-30']
    a=accepted(application,body)
    active=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert active.status_code==200,active.text
    with Session() as db:
        assert db.get(WorkoutPlan,pid).payload==before
        assert (db.get(WorkoutSetLog,rid).reps,db.get(WorkoutSetLog,rid).weight,db.get(WorkoutSetLog,rid).rpe)==(9,12,None)
