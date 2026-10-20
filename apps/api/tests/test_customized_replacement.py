"""Explicit replacement through the registered application, on disposable PostgreSQL."""
from copy import deepcopy
from uuid import uuid4
from test_customized_application import application, accepted, post, request


def activate(app, proposal=None):
    c,h,_,_=app;p=proposal or accepted(app)
    r=post(c,h,f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert r.status_code==200,r.text
    return r.json()


def replacement(app,old,body=None):
    c,h,_,_=app
    return post(c,h,f"/customized/proposals/{old['proposal_id']}/replacement",dict(expected_revision=old['revision'],request=body or request()))


def accept_proposal(app,p):
    c,h,_,_=app
    ch=post(c,h,f"/customized/proposals/{p['proposal_id']}/challenge",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert ch.status_code==200,ch.text
    ch=ch.json()
    assert ch['terms']['summary']['replacement']['plan_id']==p['snapshot']['replacement']['plan_id']
    a=post(c,h,f"/customized/proposals/{p['proposal_id']}/accept",dict(protocol='compact-candidate-consent-v2',expected_revision=ch['revision'],snapshot_hash=ch['snapshot_hash'],challenge=ch['challenge'],terms_hash=ch['terms_hash'],summary_hash=ch['summary_hash'],mode='customized',agree=True))
    assert a.status_code==200,a.text
    return a.json()


def test_unstarted_replacement_explicit_consent_atomic_provenance_retry(application):
    c,h,Session,_=application;old=activate(application)
    preview=replacement(application,old)
    assert preview.status_code==200,preview.text
    p=preview.json();assert p['snapshot']['replacement']['kind']=='same_week_unstarted'
    a=accept_proposal(application,p)
    path=f"/customized/proposals/{a['proposal_id']}/activate";body=dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash'])
    new=post(c,h,path,body,'replace-once');assert new.status_code==200,new.text
    assert post(c,h,path,body,'replace-once').json()==new.json()
    from app.models import WorkoutPlan
    with Session() as db:
        previous=db.get(WorkoutPlan,old['active_plan_id']);current=db.get(WorkoutPlan,new.json()['active_plan_id'])
        assert previous.payload['schedule']['mode']=='selected_dates_superseded_v1'
        assert previous.payload['schedule']['superseded_by_plan_id']==current.id
        assert current.payload['customized']['replacement']['plan_id']==previous.id
        assert previous.payload['customized']['consent_receipt']==old['consent_receipt']
    assert c.get(f"/customized/proposals/{old['proposal_id']}",headers=h).json()['state']=='superseded'
    assert len(c.get('/customized/active',headers=h).json()['plans'])==1
    assert c.get('/workout/today',headers=h).json()['plan_id']==new.json()['active_plan_id']


def test_started_replacement_retains_current_week_and_all_voided_history(application):
    c,h,Session,_=application;old=activate(application)
    today=c.get('/workout/today',headers=h).json();e=today['exercises'][0];wid=today['workout_occurrence_id']
    logged=post(c,h,f'/workout/{wid}/log-set',dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10))
    assert logged.status_code==200,logged.text
    before=c.get(f'/workout/{wid}/progress',headers=h).json()
    rejected=replacement(application,old)
    assert rejected.status_code==409 and 'future_week' in rejected.text,rejected.text
    body=request();body['selected_dates']=['2026-10-26','2026-10-28','2026-10-30']
    future=replacement(application,old,body);assert future.status_code==200,future.text
    p=future.json();assert p['snapshot']['replacement']['kind']=='future_week'
    assert p['snapshot']['replacement']['preserved_work']
    new=activate(application,accept_proposal(application,p))
    assert new['active_plan_id']!=old['active_plan_id']
    assert c.get('/workout/today',headers=h).json()['workout_occurrence_id']==wid
    assert c.get(f'/workout/{wid}/progress',headers=h).json()==before


def test_decline_foreign_owner_and_stale_history_cannot_replace(application):
    c,h,_,account=application;old=activate(application)
    p=replacement(application,old).json()
    declined=post(c,h,f"/customized/proposals/{p['proposal_id']}/decline",dict(expected_revision=p['revision']))
    assert declined.status_code==200
    assert c.get(f"/customized/proposals/{old['proposal_id']}",headers=h).json()['state']=='active'
    foreign=c.post('/auth/register',json={**account,'email':uuid4().hex+'@example.com'}).json()
    r=post(c,{'Authorization':'Bearer '+foreign['access_token']},f"/customized/proposals/{old['proposal_id']}/replacement",dict(expected_revision=old['revision'],request=request()))
    assert r.status_code==404,r.text
    p=replacement(application,old).json();a=accept_proposal(application,p)
    today=c.get('/workout/today',headers=h).json();e=today['exercises'][0]
    log=post(c,h,f"/workout/{today['workout_occurrence_id']}/log-set",dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10))
    assert log.status_code==200,log.text
    r=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert r.status_code==409,r.text
    assert c.get(f"/customized/proposals/{old['proposal_id']}",headers=h).json()['state']=='active'


def test_concurrent_replacements_one_winner_and_old_occurrence_cannot_be_logged(application):
    from concurrent.futures import ThreadPoolExecutor
    c,h,Session,_=application;old=activate(application)
    old_today=c.get('/workout/today',headers=h).json()
    proposals=[accept_proposal(application,replacement(application,old).json()) for _ in range(2)]
    def attempt(p):
        return post(c,h,f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,proposals))
    assert sorted(r.status_code for r in results)==[200,409]
    e=old_today['exercises'][0]
    stale=post(c,h,f"/workout/{old_today['workout_occurrence_id']}/log-set",dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10))
    assert stale.status_code==409,stale.text
    assert len(c.get('/customized/active',headers=h).json()['plans'])==1


def test_replacement_failure_rolls_back_plan_and_both_lifecycle_heads(application,monkeypatch):
    from app.customized_postgres import _Transaction
    from app.customized_lifecycle_models import LifecycleError
    from app.models import WorkoutPlan
    c,h,Session,_=application;old=activate(application)
    p=accept_proposal(application,replacement(application,old).json())
    original=_Transaction.remember
    def fail(self,subject,key,digest,response):raise LifecycleError('synthetic_failure_after_write')
    monkeypatch.setattr(_Transaction,'remember',fail)
    r=post(c,h,f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
    assert r.status_code==409,r.text
    monkeypatch.setattr(_Transaction,'remember',original)
    assert c.get(f"/customized/proposals/{old['proposal_id']}",headers=h).json()['state']=='active'
    assert c.get(f"/customized/proposals/{p['proposal_id']}",headers=h).json()['state']=='accepted_candidate'
    with Session() as db:
        row=db.get(WorkoutPlan,old['active_plan_id'])
        assert row.payload['schedule']['mode']=='selected_dates_v1'
        assert db.query(WorkoutPlan).filter_by(user_id=row.user_id).count()==1
    assert activate(application,p)['state']=='active'


def test_replacement_revision_keeps_target_and_voids_never_restore_eligibility(application):
    c,h,_,_=application;old=activate(application)
    p=replacement(application,old).json()
    changed=request();changed.update(bundle_id='longer-current',cap_minutes=90)
    r=post(c,h,f"/customized/proposals/{p['proposal_id']}/revisions",dict(expected_revision=p['revision'],request=changed))
    assert r.status_code==200,r.text
    revised=r.json();assert revised['snapshot']['replacement']['plan_id']==old['active_plan_id']
    assert revised['snapshot']['preview']['sessions'][0]['exercises']!=p['snapshot']['preview']['sessions'][0]['exercises']
    accept_proposal(application,revised)
    today=c.get('/workout/today',headers=h).json();e=today['exercises'][0];wid=today['workout_occurrence_id']
    assert post(c,h,f'/workout/{wid}/log-set',dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10)).status_code==200
    assert post(c,h,f'/workout/{wid}/undo-last-set',dict(command_id=uuid4().hex,exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'])).status_code==200
    assert c.get(f'/workout/{wid}/progress',headers=h).json()['completed_total']==0
    r=replacement(application,old)
    assert r.status_code==409 and 'future_week' in r.text,r.text


def test_reused_service_does_not_inherit_replacement_permission(application):
    from test_customized_rescheduling import bound
    c,h,_,_=application;old=activate(application)
    service,actor=bound(application)
    p=service.create_replacement(actor,old['proposal_id'],request(),expected_revision=old['revision'],idempotency_key=uuid4().hex)
    assert p['snapshot']['replacement']['plan_id']==old['active_plan_id']
    ordinary=service.create(actor,request(),idempotency_key=uuid4().hex)
    assert 'replacement' not in ordinary['snapshot']
    assert 'retained_week_occurrence_requires_resolution' in ordinary['blocking_reasons']
    assert service.schedule.exclude_plan is None and service.replacement is None


def test_normalized_unconfigured_inventory_request_can_replace(application):
    c,h,_,_=application;old=activate(application)
    data=deepcopy(old['snapshot']['request'])
    assert data.get('inventory_revision') is None
    p=replacement(application,old,data)
    assert p.status_code==200,p.text
    assert p.json()['snapshot']['replacement']['plan_id']==old['active_plan_id']
