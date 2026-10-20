"""Account-owned real inventory and corrected exposure admission on disposable PG."""
from copy import deepcopy
from uuid import uuid4
from test_customized_application import application, request, accepted, post


def inventory():
    from core_engine.customized.library import review_catalog
    variants=[e.variant_id for e in review_catalog().exercises if e.load_identity.implement=='dumbbell']
    return dict(location_id='actual-gym',location_name='My actual gym',equipment=['dumbbell','bench','bodyweight','floor'],
        unavailable_variants=[],setups=[dict(key='rack-one',label='Matched dumbbells',kind='dumbbell',unit='kg',
        weights=[dict(weight=w,count=2) for w in (10,11,12)],plates=[],bar_weight=None,stack=None,
        min_load=None,max_load=None,setup_note='Matched pairs from rack; same handles and setup')],
        assignments={v:'rack-one' for v in variants},strength_reports=[])


def save(c,h,data=None,revision=0):
    return c.put('/customized/profile',headers=h,json=dict(expected_revision=revision,profile=data or inventory()))


def test_inventory_is_owned_durable_versioned_and_stale_write_safe(application):
    c,h,_,_=application
    r=save(c,h)
    assert r.status_code==200,r.text
    assert r.json()['revision']==1
    assert c.get('/customized/profile',headers=h).json()==r.json()
    modified=inventory();modified['location_name']='Edited without deleting workout records'
    assert save(c,h,modified,0).status_code==409
    assert save(c,h,modified,1).json()['revision']==2
    other=c.post('/auth/register',json=dict(email=f'{uuid4().hex}@example.com',name='Other',password='Synthetic-only-safe-123!')).json()
    oh={'Authorization':'Bearer '+other['access_token']}
    assert c.get('/customized/profile',headers=oh).json()['revision']==0
    assert c.get('/customized/profile').status_code==401
    assert c.post('/customized/session/revoke',headers=h).status_code==200
    assert save(c,h,modified,2).status_code==401
    assert c.get('/customized/profile',headers=h).status_code==401


def test_inventory_filters_generation_and_is_bound_to_consent(application):
    c,h,_,_=application
    assert save(c,h).status_code==200
    body=request();body['equipment']=inventory()['equipment'];body['inventory_revision']=1
    p=post(c,h,'/customized/proposals',body)
    assert p.status_code==200,p.text
    p=p.json()
    assert p['snapshot']['inventory']['revision']==1
    assert all(not e['variant_id'].startswith('gym_') for s in p['snapshot']['preview']['sessions'] for e in s['exercises'])
    e=p['snapshot']['evidence']['result']['plan']['sessions'][0]['exercises'][0]['exercise']
    assert e['attainable_loads']==[10,11,12]
    updated=inventory();updated['setups'][0]['weights']=[dict(weight=11,count=2)]
    assert save(c,h,updated,1).status_code==200
    stale=post(c,h,f"/customized/proposals/{p['proposal_id']}/challenge",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert stale.status_code==409,stale.text


def test_empty_or_invalid_inventory_never_invents_weights(application):
    c,h,_,_=application
    bad=inventory();bad['setups'][0]['weights'][0]['weight']=-1
    assert save(c,h,bad).status_code==422
    data=inventory();data['equipment']=[];data['setups']=[];data['assignments']={}
    assert save(c,h,data).status_code==200
    body=request();body['equipment']=[];body['inventory_revision']=1
    p=post(c,h,'/customized/proposals',body)
    assert p.status_code==200,p.text
    assert p.json()['blocking_reasons'] or not p.json()['snapshot']['preview']['sessions']


def gym_inventory():
    from core_engine.customized.library import review_catalog
    data=inventory();data['equipment']=request()['equipment']
    for e in review_catalog().exercises:
        if e.load_identity.implement=='machine':
            key='station-'+e.variant_id
            setup=deepcopy(data['setups'][0]);setup.update(key=key,label=e.name,kind='machine_stack',setup_note='Seat 3; unchanged lever, pin and range')
            data['setups'].append(setup);data['assignments'][e.variant_id]=key
    return data


def activated_inventory(application):
    c,h,_,_=application
    assert save(c,h,gym_inventory()).status_code==200
    body=request();body['inventory_revision']=1
    a=accepted(application,body)
    result=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert result.status_code==200,result.text
    today=c.get('/workout/today',headers=h).json()
    return today,today['exercises'][0]


def test_complete_easy_exposure_gives_attainable_next_load_and_correction_rebuilds(application):
    c,h,_,_=application;t,e=activated_inventory(application)
    logs=[]
    for i in range(1,e['sets']+1):
        r=post(c,h,f"/workout/{t['workout_occurrence_id']}/log-set",dict(command_id=uuid4().hex,exercise_id=e['id'],
            exercise_occurrence_id=e['exercise_occurrence_id'],set_index=i,reps=e['rep_range'][1],weight=10,
            actual_rir=5,technique_quality='acceptable',pain=False))
        assert r.status_code==200,r.text
        logs.append(r.json())
    assert logs[-1]['next_working_weight']==11,logs[-1]
    assert logs[-1]['decision_trace']['load_decision']['action']=='increase'
    assert len(logs[-1]['decision_trace']['load_decision']['calibration']['evidence_ids'])==e['sets']
    correction=post(c,h,f"/workout/set/{logs[-1]['id']}/correct",dict(command_id=uuid4().hex,reps=e['rep_range'][1],weight=10,
        actual_rir=None,reason='Effort was not reliably recorded'))
    assert correction.status_code==200,correction.text
    assert correction.json()['live_recommendation']['recommended_weight'] is None
    fresh=c.get('/workout/today',headers=h).json()['exercises'][0]
    assert fresh['customized_load_decision']['recommended_weight'] is None
    audit=c.get(f"/workout/set/{logs[-1]['id']}/audit",headers=h)
    assert audit.status_code==200


def test_optional_strength_is_information_not_a_percentage_prescription(application):
    c,h,_,_=application
    data=gym_inventory();data['strength_reports']=[dict(report_id='reported',variant_id='gym_leg_press',setup_key='station-gym_leg_press',
        kind='e1rm',load=100,unit='kg',observed_on='2026-10-18',confirmed=True,method_reference='User-reported estimate; uncertain')]
    assert save(c,h,data).status_code==200
    t,e=activated_inventory_without_save(application)
    decision=e['customized_load_decision']
    assert decision['recommended_weight'] is None
    # A report for an unselected variant is never transferred.
    data['strength_reports'][0].update(report_id='reentered-for-actual-variant',variant_id=e['id'],setup_key=data['assignments'][e['id']])
    assert save(c,h,data,1).status_code==200
    fresh=c.get('/workout/today',headers=h).json()['exercises'][0]['customized_load_decision']
    assert fresh['recommended_weight'] is None
    assert 'self_report_information_only_no_working_load_conversion' in fresh['reason_codes']
    assert fresh['calibration']['strength_information'][0]['report_id']=='reentered-for-actual-variant'
    # Persist the dated optional report audit with an actual receipt, not only a GET.
    logged=post(c,h,f"/workout/{t['workout_occurrence_id']}/log-set",dict(command_id=uuid4().hex,exercise_id=e['id'],
        exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=10,weight=10,technique_quality='acceptable',pain=False))
    assert logged.status_code==200,logged.text
    assert logged.json()['decision_trace']['load_decision']['calibration']['strength_information'][0]['observed_on']=='2026-10-18'
    assert c.get(f"/workout/set/{logged.json()['id']}/audit",headers=h).status_code==200


def activated_inventory_without_save(application):
    c,h,_,_=application;body=request();body['inventory_revision']=1
    a=accepted(application,body)
    r=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert r.status_code==200,r.text
    t=c.get('/workout/today',headers=h).json();return t,t['exercises'][0]


def test_application_uses_original_profile_without_legacy_numerical_owner(application,monkeypatch):
    import app.customized_preview_service as module
    def forbidden(**kwargs):raise AssertionError('Legacy numerical profile owner must not execute')
    monkeypatch.setattr(module,'build_generated_training_profile',forbidden)
    c,h,_,_=application
    p=post(c,h,'/customized/proposals',request())
    assert p.status_code==200,p.text
    assert p.json()['snapshot']['preview']['trace']['normalizer']=='core_engine.customized.models.CustomizedProfile'


def test_legacy_generator_redirects_to_consent_bound_original_workflow(application):
    from app.models import User,WorkoutPlan
    import jwt
    c,h,Session,_=application
    # Existing verified synthetic account; direct fixture setup only.
    with Session() as db:
        user=db.query(User).filter_by(email=application[3]['email']).one()
        user.selected_program_id='full_body_v1';user.split_preference='full_body';user.days_available=3
        db.commit();uid=user.id
    r=c.post('/plan/generate-week',headers=h,json={'template_id':'full_body_v1'})
    assert r.status_code==409,r.text
    assert r.json()['detail']['code']=='customized_preview_required'
    assert r.json()['detail']['path']=='/customize'
    with Session() as db:assert db.query(WorkoutPlan).filter_by(user_id=uid).count()==0


def test_inventory_change_preserves_receipts_but_removes_unattainable_next_load(application):
    from app.models import WorkoutSetLog
    c,h,Session,_=application;t,e=activated_inventory(application)
    ids=[]
    for i in range(1,e['sets']+1):
        r=post(c,h,f"/workout/{t['workout_occurrence_id']}/log-set",dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],
            set_index=i,reps=e['rep_range'][1],weight=10,actual_rir=5,technique_quality='acceptable',pain=False))
        assert r.status_code==200,r.text
        ids.append(r.json()['id'])
    data=gym_inventory()
    for s in data['setups']:s['weights']=[dict(weight=11,count=2),dict(weight=12,count=2)]
    assert save(c,h,data,1).status_code==200
    fresh=c.get('/workout/today',headers=h).json()['exercises'][0]['customized_load_decision']
    assert fresh['recommended_weight'] is None
    assert 'performed_load_not_in_inventory' in fresh['reason_codes']
    with Session() as db:
        assert [r.id for r in db.query(WorkoutSetLog).filter(WorkoutSetLog.id.in_(ids)).order_by(WorkoutSetLog.set_index)]==ids


def test_report_identity_is_not_rebound_by_editing_the_setup(application):
    c,h,_,_=application;data=gym_inventory()
    data['strength_reports']=[dict(report_id='same-report',variant_id='db_goblet',setup_key='rack-one',kind='1rm',load=30,unit='kg',observed_on='2026-10-18',confirmed=True,method_reference=None)]
    first=save(c,h,data).json();fingerprint=first['profile']['strength_reports'][0]['setup_fingerprint']
    data['setups'][0]['setup_note']='A different handle geometry and recorded range'
    second=save(c,h,data,1).json()['profile']['strength_reports'][0]
    assert second['setup_fingerprint']==fingerprint
    assert second['confirmed'] is False


def test_inventory_updates_serialize_on_postgresql(application):
    from concurrent.futures import ThreadPoolExecutor
    c,h,_,_=application
    assert save(c,h).status_code==200
    a=inventory();a['location_name']='Edit A'
    b=inventory();b['location_name']='Edit B'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda data:save(c,h,data,1),(a,b)))
    assert sorted(r.status_code for r in responses)==[200,409]
    assert c.get('/customized/profile',headers=h).json()['revision']==2


def test_scoped_load_query_uses_date_index_with_large_old_history(application):
    from datetime import date,datetime
    from sqlalchemy import text
    from app.models import WorkoutOccurrence,WorkoutSetLog,User
    from app.customized_load_evidence import exposure_query,completed_exposures
    c,h,Session,account=application
    with Session() as db:
        user=db.query(User).filter_by(email=account['email']).one();uid=user.id
        ids=[str(uuid4()) for _ in range(12000)]
        db.bulk_insert_mappings(WorkoutOccurrence,[dict(id=oid,user_id=uid,plan_id='synthetic-old',week_start=date(2020,1,6),
            scheduled_date=date(2020,1,6),schedule_timezone='UTC',placement_revision=1,session_slot=i,workout_id=oid,
            program_id='customized_full_body_v1',payload={}) for i,oid in enumerate(ids)])
        db.bulk_insert_mappings(WorkoutSetLog,[dict(user_id=uid,workout_id=oid,workout_occurrence_id=oid,exercise_occurrence_id='old',
            primary_exercise_id='db_goblet',exercise_id='db_goblet',set_index=1,reps=8,weight=10,set_kind='work') for oid in ids])
        # The large synthetic cohort is visible to this query but never committed.
        # Repeated qualification must not accumulate user-lifetime fixtures.
        # Additive index from migration0023, only in the verified fixture DB.
        db.execute(text('CREATE INDEX IF NOT EXISTS ix_customized_load_cohort_date ON workout_occurrences(user_id,program_id,scheduled_date)'))
        db.execute(text('ANALYZE workout_occurrences'));db.execute(text('ANALYZE workout_set_logs'))
        query=exposure_query(db,uid,date(2026,10,19),['db_goblet'],max_age_days=28)
        assert query.count()==0
        assert completed_exposures(db,uid,date(2026,10,19),['db_goblet'],max_age_days=28)==()
        sql=str(query.statement.compile(db.bind,compile_kwargs={'literal_binds':True}))
        explain=db.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql)).scalar_one()
        import json
        assert 'ix_customized_load_cohort_date' in json.dumps(explain),explain
        print('LOAD_QUERY_12000',json.dumps(explain))
        db.rollback()


def test_additive_inventory_migration_preserves_existing_account_and_occurrence(application):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.models import User,WorkoutOccurrence
    _,_,Session,_=application
    schema='m4inventory_'+uuid4().hex[:12]
    with Session().get_bind().begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
        conn.execute(text(f'SET LOCAL search_path TO {schema}'))
        User.__table__.create(conn);WorkoutOccurrence.__table__.create(conn)
        conn.execute(User.__table__.insert().values(id='retained-user',email='retained@example.com',name='Synthetic',password_hash='synthetic-hash'))
        from datetime import date
        conn.execute(WorkoutOccurrence.__table__.insert().values(id='retained-occurrence',user_id='retained-user',plan_id='retained-plan',week_start=date(2026,10,19),session_slot=0,workout_id='retained',payload={'retained':True}))
        before=conn.execute(text('SELECT row_to_json(o) FROM workout_occurrences o')).scalar_one()
        path=Path(__file__).parents[1]/'alembic/versions/0023_customized_inventory.py'
        spec=importlib.util.spec_from_file_location('inventory_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with Operations.context(MigrationContext.configure(conn)):module.upgrade()
        assert conn.execute(text('SELECT row_to_json(o) FROM workout_occurrences o')).scalar_one()==before
        assert conn.execute(text('SELECT count(*) FROM users')).scalar_one()==1
        assert conn.execute(text('SELECT count(*) FROM customized_equipment_profiles')).scalar_one()==0
        assert conn.execute(text("SELECT count(*) FROM pg_indexes WHERE schemaname=:s AND indexname='ix_customized_load_cohort_date'"),{'s':schema}).scalar_one()==1
