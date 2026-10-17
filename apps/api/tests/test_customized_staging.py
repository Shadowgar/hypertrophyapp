"""Staging boundary tests: existing JWT, explicit entitlement, retained calendar."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, timedelta
import hashlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from research.m4c3a.fixtures import demo_context,demo_request,demo_server
from research.m4c3b1.demo import proposed_request


def test_staging_modules_exist_as_explicit_unregistered_adapters():
    import importlib.util
    assert importlib.util.find_spec('app.customized_staging_auth'), 'Missing explicit entitlement/session adapter'
    assert importlib.util.find_spec('app.customized_staging_schedule'), 'Missing read-only calendar revision adapter'


@pytest.fixture
def staged(tmp_path):
    from app.customized_staging_auth import SessionGrant,StagingAccessGate
    from app.customized_staging_schedule import CalendarWindow,ReadOnlyCalendarAdapter
    from app.customized_staging_http import create_staging_app
    from app.customized_lifecycle import LifecycleService
    from app.deps import get_db
    from app.models import User
    from app.security import create_access_token
    from research.m4c3b1.store import DisposableProposalStore
    now=demo_context().planning_instant
    users={name:User(id=name,password_hash='synthetic-credential-'+name) for name in ('alice','bob')}
    tokens={name:create_access_token(name) for name in users}
    class Access:
        grants={}
        def resolve(self,subject,session_id):return self.grants.get((subject,session_id))
    access=Access()
    for name in users:
        binding=hashlib.sha256(('Bearer '+tokens[name]).encode()).hexdigest()
        grant=SessionGrant(name,binding,hashlib.sha256(users[name].password_hash.encode()).hexdigest(),
            'explicit-test-entitlement-'+name,1,('customized:preview','customized:proposal'),now-timedelta(days=1),now+timedelta(days=1),True)
        access.grants[name,binding]=grant
    gate=StagingAccessGate(access,clock=lambda:now,current_credential_revision=lambda subject:
        hashlib.sha256(users[subject].password_hash.encode()).hexdigest() if subject in users else None)
    class Calendar:
        rows=()
        revision='calendar-1'
        def read(self,subject,timezone,start,end):
            return CalendarWindow(subject,timezone,start,end,self.revision,'pr83@3f4927b3cdcca1e8655337b30b93894741bfca9c',self.rows,True)
    source=Calendar()
    schedule=ReadOnlyCalendarAdapter(source,context=demo_context())
    service=LifecycleService(server=replace(demo_server(),allowed_subjects=('alice','bob')),
        store=DisposableProposalStore.create(tmp_path/'stage.sqlite',disposable_root=tmp_path),schedule=schedule,clock=lambda:now,
        comparison_pairs=(('shorter-current','longer-current'),),authorize_actor=gate.authorize)
    class Lookup:
        def filter(self,predicate):self.subject=predicate.right.value;return self
        def first(self):return users.get(self.subject)
    def accounts():yield SimpleNamespace(query=lambda model:Lookup())
    app=create_staging_app(service=service,access_gate=gate,trusted_origin='http://testserver',initial_request=proposed_request())
    app.dependency_overrides[get_db]=accounts
    client=TestClient(app)
    def post(path,data,key='create',subject='alice'):
        return client.post(path,json=data,headers={'Authorization':'Bearer '+tokens[subject],
            'Origin':'http://testserver','Idempotency-Key':key})
    yield SimpleNamespace(service=service,client=client,post=post,access=access,gate=gate,source=source,users=users,tokens=tokens,now=now)


def create(staged):
    response=staged.post('/customized/proposals',proposed_request())
    assert response.status_code==200,response.text
    return response.json()


def prepare(staged,p):
    return staged.post('/customized/proposals/'+p['proposal_id']+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'prepare').json()


def test_jwt_is_not_an_entitlement_and_revocation_denies_cached_retries(staged):
    p=create(staged)
    key=next(k for k in staged.access.grants if k[0]=='alice')
    grant=staged.access.grants.pop(key)
    assert staged.post('/customized/proposals',proposed_request()).status_code==403
    staged.access.grants[key]=replace(grant,enabled=False)
    assert staged.post('/customized/proposals',proposed_request()).status_code==401
    staged.access.grants[key]=replace(grant,expires_at=staged.now)
    assert staged.post('/customized/proposals',proposed_request()).status_code==401
    staged.access.grants[key]=grant
    staged.users['alice'].password_hash='changed-after-reset'
    assert staged.post('/customized/proposals',proposed_request()).status_code==401
    assert p['can_activate'] is False


def test_scope_is_server_owned_and_cross_account_object_is_404(staged):
    p=create(staged)
    for id in (p['proposal_id'],'unknown'):
        r=staged.client.get('/customized/proposals/'+id,headers={'Authorization':'Bearer '+staged.tokens['bob']})
        assert r.status_code==404 and r.json()=={'status':'not_found'}
    key=next(k for k in staged.access.grants if k[0]=='alice')
    staged.access.grants[key]=replace(staged.access.grants[key],scopes=('customized:preview',))
    assert staged.post('/customized/proposals',proposed_request()).status_code==403


def test_account_grant_is_rechecked_before_commit(staged):
    gate=staged.gate
    calls=0
    def revoke_during_command(actor):
        nonlocal calls
        calls+=1
        gate.authorize(actor)
        if calls==2:
            key=next(k for k in staged.access.grants if k[0]=='alice')
            staged.access.grants[key]=replace(staged.access.grants[key],enabled=False)
    staged.service.authorize_actor=revoke_during_command
    response=staged.post('/customized/proposals',proposed_request())
    assert response.status_code==401
    with staged.service.store.transaction() as tx:
        assert tx.retry('alice','create') is None


def row(*,id='authored-1',day=date(2026,10,25),revision=1,state='completed',void=False,**changes):
    from app.customized_staging_schedule import CalendarOccurrence
    return replace(CalendarOccurrence('alice',id,'source-plan',day-timedelta(days=day.weekday()),day,'America/New_York',revision,
        state,'authored','immutable-source-hash',('source-slot-a','source-slot-b'),void,'effective-history-1'),**changes)


def test_calendar_read_projector_retains_local_dates_revisions_void_history_and_no_writes(staged):
    original=(row(),row(id='future',day=date(2026,11,3),state='planned',week_start=date(2026,11,2)),
        row(id='moved',day=date(2026,11,3),state='planned',week_start=date(2026,11,2)),
        row(id='moved',day=date(2026,11,4),state='planned',revision=2,week_start=date(2026,11,2)),
        row(id='cancelled',day=date(2026,10,28),state='planned'),row(id='cancelled',day=date(2026,10,28),state='planned',revision=2,void=True))
    staged.source.rows=original
    p=create(staged);s=p['snapshot']['schedule']
    assert [(o['occurrence_id'],o['local_date']) for o in s['occurrences']]==[('authored-1','2026-10-25'),('future','2026-11-03'),('moved','2026-11-04')]
    assert s['source_kind']=='synthetic'
    assert p['snapshot']['request']['selected_dates']==['2026-10-27','2026-10-29','2026-11-01']
    assert staged.source.rows==original
    c=prepare(staged,p)
    staged.source.revision='undo-or-edit-2'
    data=dict(protocol='compact-candidate-consent-v2',expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],
        challenge=c['challenge'],terms_hash=c['terms_hash'],summary_hash=c['summary_hash'],mode='customized',agree=True)
    response=staged.post('/customized/proposals/'+p['proposal_id']+'/accept',data,'accept-stale')
    assert response.status_code==409 and response.json()['status']=='stale_schedule'


@pytest.mark.parametrize('changes',[{'subject':'bob'},{'source_revision':''}])
def test_foreign_or_unverified_calendar_envelope_fails_closed(staged,changes):
    old=staged.source.read
    staged.source.read=lambda *args:replace(old(*args),**changes)
    r=staged.post('/customized/proposals',proposed_request())
    assert r.status_code==409 and r.json()['status']=='invalid_calendar_context'


def test_started_work_cannot_be_erased_by_void_or_rewritten_as_planned(staged):
    staged.source.rows=(row(day=date(2026,10,26),week_start=date(2026,10,26),state='started'),
        row(day=date(2026,10,26),week_start=date(2026,10,26),revision=2,state='planned',void=True))
    response=staged.post('/customized/proposals',proposed_request())
    assert response.status_code==409 and response.json()['status']=='frozen_occurrence_changed'


def test_in_week_authored_work_is_visible_and_blocks_consent_without_replacement(staged):
    staged.source.rows=(row(day=date(2026,10,26),week_start=date(2026,10,26),state='started'),)
    p=create(staged)
    assert 'retained_week_occurrence_requires_resolution' in p['blocking_reasons']
    r=staged.post('/customized/proposals/'+p['proposal_id']+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'challenge')
    assert r.status_code==409 and r.json()['status']=='schedule_conflict'


def test_concise_consent_is_exact_version_bound_and_retains_all_audit_terms(staged):
    p=create(staged);c=prepare(staged,p)
    assert c['consent_protocol']=='compact-candidate-consent-v2'
    assert len(c['audit_acknowledgements'])==20
    summary=c['summary']
    assert summary['candidate']['weekly_sets']==33 and summary['reference']['weekly_sets']==45
    assert summary['candidate']['upper_minutes']==[57.5,59,57.5]
    assert summary['reference']['upper_minutes']==[69,70.5,69]
    assert len(summary['workload_changes'])==12 and len(summary['proposed_range_conflicts'])==6
    assert summary['scientific_status']=='review_required'
    assert 'required_acknowledgements' not in c  # Not routine UI checkboxes.
    data=dict(protocol='compact-candidate-consent-v2',expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],
        challenge=c['challenge'],terms_hash=c['terms_hash'],summary_hash=c['summary_hash'],mode='customized',agree=True)
    prefix='/customized/proposals/'+p['proposal_id']
    bad=staged.post(prefix+'/accept',{**data,'summary_hash':'0'*64},'tampered')
    assert bad.status_code==403
    accepted=staged.post(prefix+'/accept',data,'accept').json()
    assert accepted['state']=='accepted_candidate'
    receipt=accepted['consent_receipt']
    assert receipt['protocol']==data['protocol'] and receipt['summary_hash']==c['summary_hash']
    assert len(receipt['acknowledgements'])==20 and len(receipt['audit_summary']['workload_changes'])==12
    assert staged.post(prefix+'/accept',data,'accept').json()==accepted
    r=staged.post(prefix+'/authorization',{'expected_revision':accepted['revision']},'authorize').json()
    assert r['state']=='activation_blocked' and r['can_activate'] is False
    assert r['authorization']['eligible'] is False


def test_known_adjacent_work_blocks_insufficient_gap_without_shifting_dates(staged):
    staged.source.rows=(row(id='next-monday',day=date(2026,11,2),state='planned'),)
    p=create(staged)
    assert 'schedule_spacing_conflict' in p['snapshot']['preview']['reasons']
    r=staged.post('/customized/proposals/'+p['proposal_id']+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'challenge')
    assert r.status_code==409 and r.json()['status']=='candidate_infeasible'
    assert p['snapshot']['request']['selected_dates']==['2026-10-27','2026-10-29','2026-11-01']


def compact_command(c):
    return dict(protocol='compact-candidate-consent-v2',expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],
        challenge=c['challenge'],terms_hash=c['terms_hash'],summary_hash=c['summary_hash'],mode='customized',agree=True)


def test_compact_protocol_replay_expiry_revision_and_client_authority_boundaries(staged):
    p=create(staged);c=prepare(staged,p);prefix='/customized/proposals/'+p['proposal_id'];command=compact_command(c)
    assert staged.post(prefix+'/accept',{**command,'protocol':'legacy'},'wrong-protocol').status_code==422
    assert staged.post(prefix+'/accept',{**command,'acknowledgements':[]},'client-audit').status_code==422
    old=staged.service.clock
    staged.service.clock=lambda:staged.now+timedelta(minutes=10)
    r=staged.post(prefix+'/accept',command,'expired')
    assert r.status_code==409 and r.json()['status']=='consent_challenge_expired'
    staged.service.clock=old
    revised=staged.post(prefix+'/revisions',dict(expected_revision=c['revision'],request={**proposed_request(),'cap_minutes':90,'bundle_id':'longer-current'}),'revise').json()
    assert revised['plan_version']==2 and revised['consent_receipt'] is None
    r=staged.post(prefix+'/accept',command,'old-candidate')
    assert r.status_code==409 and r.json()['status']=='challenge_consumed_or_stale'
    assert staged.post('/customized/proposals',{**proposed_request(),'owner_id':'bob'},'spoof').status_code==422


@pytest.mark.parametrize('change',[{'skill':None},{'restrictions':None},{'restrictions':['unmapped-medical-clearance']},{'training_context':'unknown'}])
def test_staged_unknown_inputs_cannot_become_medical_skill_or_effort_clearance(staged,change):
    p=staged.post('/customized/proposals',{**proposed_request(),**change}).json()
    assert not p['snapshot']['preview']['sessions']
    r=staged.post('/customized/proposals/'+p['proposal_id']+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'prepare')
    assert r.status_code==409


def test_staged_missing_inventory_and_observed_rir_do_not_invent_load(staged):
    server=staged.service.server
    bundles=[]
    for bundle in server.bundles:
        catalog=replace(bundle.catalog,exercises=tuple(replace(e,attainable_loads=()) for e in bundle.catalog.exercises))
        bundles.append(replace(bundle,catalog=catalog))
    staged.service.server=replace(server,bundles=tuple(bundles))
    p=create(staged)
    exercises=[e for s in p['snapshot']['preview']['sessions'] for e in s['exercises']]
    assert exercises and all(e['working_load'] is None and not e['observed_effort'] for e in exercises)
    assert p['prescriptive'] is False and p['snapshot']['authority']['inventory']=='synthetic'


def test_duplicate_compact_accept_has_one_receipt_and_retry_does_not_restore_withdrawal(staged):
    from concurrent.futures import ThreadPoolExecutor
    p=create(staged);c=prepare(staged,p);prefix='/customized/proposals/'+p['proposal_id'];command=compact_command(c)
    def accept(_):return staged.post(prefix+'/accept',command,'same-accept')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(accept,range(2)))
    assert [r.status_code for r in results]==[200,200]
    a,b=[r.json() for r in results]
    assert a['consent_receipt']['receipt_id']==b['consent_receipt']['receipt_id']
    withdrawn=staged.post(prefix+'/withdraw',dict(expected_revision=a['revision']),'withdraw').json()
    assert withdrawn['state']=='withdrawn'
    assert staged.post(prefix+'/accept',command,'same-accept').json()==a
    current=staged.client.get(prefix,headers={'Authorization':'Bearer '+staged.tokens['alice']}).json()
    assert current['state']=='withdrawn' and current['consent_receipt'] is None


def test_calendar_source_order_is_not_a_new_schedule_revision(staged):
    staged.source.rows=(row(id='a'),row(id='b',day=date(2026,11,3),state='planned'))
    one=staged.service.schedule.resolve('alice','America/New_York')
    staged.source.rows=tuple(reversed(staged.source.rows))
    two=staged.service.schedule.resolve('alice','America/New_York')
    assert one.freshness_hash()==two.freshness_hash()


def test_actual_sqlite_account_lookup_uses_existing_verifier_and_explicit_grants(tmp_path):
    import importlib.util
    assert importlib.util.find_spec('research.m4c3b2a.fixtures'),'Missing disposable real-account fixture'
    from research.m4c3b2a.fixtures import build_staging_demo
    demo=build_staging_demo(tmp_path,origin='http://testserver')
    client=TestClient(demo.app)
    headers={'Authorization':'Bearer '+demo.tokens['alice'],'Origin':'http://testserver','Idempotency-Key':'real-account'}
    p=client.post('/customized/proposals',json=proposed_request(),headers=headers).json()
    assert p['subject']=='alice' and p['can_activate'] is False
    before=demo.accounts.private_row_count()
    demo.accounts.change_credential('alice','different-synthetic-credential-revision')
    assert client.get('/customized/proposals/'+p['proposal_id'],headers=headers).status_code==401
    assert demo.accounts.private_row_count()==before==2
    demo.accounts.close()


def test_password_reset_during_accept_rolls_back_receipt_with_fresh_orm_lookup(tmp_path):
    from research.m4c3b2a.fixtures import build_staging_demo
    demo=build_staging_demo(tmp_path,origin='http://testserver')
    client=TestClient(demo.app)
    headers={'Authorization':'Bearer '+demo.tokens['alice'],'Origin':'http://testserver'}
    def post(path,data,key):
        return client.post(path,json=data,headers={**headers,'Idempotency-Key':key})
    try:
        p=post('/customized/proposals',proposed_request(),'create').json()
        prefix='/customized/proposals/'+p['proposal_id']
        c=post(prefix+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'challenge').json()
        original=demo.service.schedule.resolve
        def reset_during_accept(*args):
            result=original(*args)
            demo.accounts.change_credential('alice','reset-during-accept')
            return result
        demo.service.schedule.resolve=reset_during_accept
        response=post(prefix+'/accept',compact_command(c),'accept-reset')
        assert response.status_code==401,response.json().get("status")
        with demo.service.store.transaction() as tx:
            current=tx.read('alice',p['proposal_id'])
            assert current['revision']==c['revision'] and current['consent_receipt'] is None
            assert tx.retry('alice','accept-reset') is None
    finally:
        demo.accounts.close()


def test_account_disappearing_during_command_cannot_commit_or_cache(staged):
    original=staged.service.schedule.resolve
    def unavailable_during_command(*args):
        result=original(*args)
        staged.users.pop('alice')  # Synthetic lookup only; no database deletion.
        return result
    staged.service.schedule.resolve=unavailable_during_command
    response=staged.post('/customized/proposals',proposed_request(),'account-unavailable')
    assert response.status_code==401,response.json().get("status")
    with staged.service.store.transaction() as tx:
        assert tx.retry('alice','account-unavailable') is None
