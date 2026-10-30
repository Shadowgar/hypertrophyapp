"""Requires the explicit owned PostgreSQL manifest; never inherited DATABASE_URL."""
import importlib.util
import os
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text


def test_postgres_adapter_is_available_without_production_registration():
    assert importlib.util.find_spec('app.customized_postgres'), 'Missing actual PostgreSQL store/session adapter'
    assert importlib.util.find_spec('app.customized_source_calendar'), 'Missing exact source read adapter'


@pytest.fixture(scope='module')
def pg():
    path=os.environ.get('C3B2B_TARGET_MANIFEST')
    if not path:pytest.skip('No explicitly verified disposable PostgreSQL target manifest supplied')
    from research.m4c3b2b.target import open_target
    engine=open_target(path)
    yield engine
    engine.dispose()


@pytest.fixture
def system(pg):
    from research.m4c3b2b.fixtures import build_system
    return build_system(pg)


def request():
    from research.m4c3b1.demo import proposed_request
    return proposed_request()


def prepared(s,subject='a'):
    actor=s.actors[subject];p=s.service.create(actor,request(),idempotency_key='create')
    c=s.service.challenge(actor,p['proposal_id'],expected_revision=p['revision'],snapshot_hash=p['snapshot_hash'],
        idempotency_key='prepare',protocol='compact-candidate-consent-v2')
    data=dict(protocol='compact-candidate-consent-v2',expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],
        challenge=c['challenge'],terms_hash=c['terms_hash'],summary_hash=c['summary_hash'],mode='customized',agree=True)
    return actor,p,c,data


def test_postgres_reconnect_replay_cas_rollback_and_consent_audit(system):
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    a=s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    assert a['state']=='accepted_candidate' and not a['can_activate']
    receipt=a['consent_receipt'];assert len(receipt['acknowledgements'])==20
    assert len(receipt['audit_summary']['workload_changes'])==12
    assert len(receipt['audit_summary']['proposed_range_conflicts'])==6
    s.engine.dispose()
    assert s.service.get(actor,p['proposal_id'])==a
    with s.store.authorized_transaction(actor) as tx:
        assert tx.history(actor.subject,p['proposal_id'])[-1]['revision']==a['revision']
    with pytest.raises(LifecycleError,match='stale_revision'):
        s.service.transition(actor,p['proposal_id'],'decline',expected_revision=c['revision'],idempotency_key='stale')
    with pytest.raises(RuntimeError):
        with s.store.authorized_transaction(actor) as tx:
            tx.remember(actor.subject,'rollback','d',{'private':'not committed'})
            raise RuntimeError('injected rollback')
    with s.store.authorized_transaction(actor) as tx:assert tx.retry(actor.subject,'rollback') is None
    w=s.service.transition(actor,p['proposal_id'],'withdraw',expected_revision=a['revision'],idempotency_key='withdraw')
    assert s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')==a
    assert s.service.get(actor,p['proposal_id'])==w and w['consent_receipt'] is None
    with pytest.raises(LifecycleError) as foreign:s.service.get(s.actors['b'],p['proposal_id'])
    assert foreign.value.status==404


@pytest.mark.parametrize('kind',['revoke','reset','rotate','calendar'])
def test_independent_connection_change_before_accept_denies_stale_authority(system,kind):
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    s.change(kind,actor.subject)
    with pytest.raises(LifecycleError) as denied:
        s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    assert denied.value.status in (401,409)
    with s.engine.begin() as conn:
        from sqlalchemy import text
        assert conn.execute(text('SELECT count(*) FROM customized_candidate_commands WHERE subject=:s AND request_key=:k'),dict(s=actor.subject,k='accept')).scalar()==0


def test_duplicate_accept_and_parallel_subjects_use_account_locks(system):
    from concurrent.futures import ThreadPoolExecutor
    s=system;actor,p,c,data=prepared(s)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=list(pool.map(lambda _:s.service.accept(actor,p['proposal_id'],data,idempotency_key='same'),range(2)))
    assert a==b
    assert a['consent_receipt']['receipt_id']==b['consent_receipt']['receipt_id']
    # Another account remains writable while this account's lock is held.
    with s.unit.account(actor.subject):
        with ThreadPoolExecutor(max_workers=1) as pool:
            other=pool.submit(s.service.create,s.actors['b'],request(),idempotency_key='parallel').result(timeout=3)
    assert other['subject']==s.actors['b'].subject


@pytest.mark.parametrize('kind',['revoke','reset','rotate','calendar'])
def test_accept_commit_and_competing_change_are_serialized(system,kind):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    entered=Event();release=Event();attempt=Event();original=s.service.schedule.resolve
    def paused(*args):
        value=original(*args);entered.set();assert release.wait(4);return value
    s.service.schedule.resolve=paused
    def change():attempt.set();s.change(kind,actor.subject)
    with ThreadPoolExecutor(max_workers=2) as pool:
        accept=pool.submit(s.service.accept,actor,p['proposal_id'],data,idempotency_key='accept-race')
        assert entered.wait(4)
        update=pool.submit(change);assert attempt.wait(2)
        # A real independent connection must be waiting on PostgreSQL's User lock.
        assert s.wait_for_lock(actor.subject), 'Competing writer did not wait on the shared account row'
        assert not update.done();release.set();accepted=accept.result(timeout=5);update.result(timeout=5)
    assert accepted['state']=='accepted_candidate'
    s.service.schedule.resolve=original
    if kind!='calendar':
        with pytest.raises(LifecycleError) as denied:s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept-race')
        assert denied.value.status==401
    else:
        # Historical receipt remains historical; no activation from edited context.
        current=s.service.get(actor,p['proposal_id']);assert not current['can_activate']
        blocked=s.service.check_activation(actor,p['proposal_id'],expected_revision=current['revision'],idempotency_key='blocked')
        assert not blocked['can_activate']


def test_real_jwt_current_user_bridge_and_server_session_identity(system):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.security import create_access_token
    from app.models import User
    from app.deps import get_db
    from app.customized_staging_http import create_staging_app
    from app.customized_lifecycle_models import LifecycleError
    s=system;subject=s.actors['a'].subject
    with Session(s.engine) as account_db:
        token=create_access_token(subject, account_db.get(User, subject).password_hash)
    header='Bearer '+token
    session_id=s.gate.issue(subject,header,entitlement_reference='explicit-test-only',scopes=('customized:preview','customized:proposal'),
        valid_from=s.service.clock()-timedelta(minutes=1),expires_at=s.service.clock()+timedelta(hours=1))
    assert len(session_id)==36 and session_id!=__import__('hashlib').sha256(header.encode()).hexdigest()
    app=create_staging_app(service=s.service,access_gate=s.gate,trusted_origin='http://testserver')
    def db():
        with Session(s.engine) as session:yield session
    app.dependency_overrides[get_db]=db
    client=TestClient(app);headers={'Authorization':header,'Origin':'http://testserver','Idempotency-Key':'jwt'}
    response=client.post('/customized/proposals',json=request(),headers=headers)
    assert response.status_code==200,response.json().get('status')
    assert response.json()['subject']==subject and not response.json()['can_activate']
    s.gate.revoke(subject,session_id)
    assert client.post('/customized/proposals',json=request(),headers=headers).status_code==401
    # Valid existing JWT without an explicit server session never gains scopes.
    with Session(s.engine) as account_db:
        other=create_access_token(s.actors['b'].subject, account_db.get(User, s.actors['b'].subject).password_hash)
    assert client.post('/customized/proposals',json=request(),headers={**headers,'Authorization':'Bearer '+other}).status_code==403


def test_corrupt_revision_replay_rejects_and_transaction_rolls_back(system):
    from sqlalchemy import text
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    before=s.service.get(actor,p['proposal_id'])
    with pytest.raises(LifecycleError,match='candidate_replay_integrity'):
        with s.store.authorized_transaction(actor) as tx:
            tx.connection.execute(text("UPDATE customized_candidate_events SET document=jsonb_set(document,'{state}','\"forged\"') WHERE subject=:s AND proposal_id=:p AND revision=1"),dict(s=actor.subject,p=p['proposal_id']))
            tx.read(actor.subject,p['proposal_id'])
    assert s.service.get(actor,p['proposal_id'])==before


def test_concurrent_distinct_commands_one_cas_winner(system):
    from concurrent.futures import ThreadPoolExecutor
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    def command(key):
        try:return s.service.transition(actor,p['proposal_id'],'decline',expected_revision=c['revision'],idempotency_key=key)['state']
        except LifecycleError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(command,('one','two')))
    assert sorted(results)==['declined','stale_revision']


def test_session_issue_requires_explicit_entitlement_and_scope_and_unknown_session_denies(system):
    from app.customized_lifecycle_models import LifecycleError
    s=system;subject=s.actors['a'].subject
    with pytest.raises(LifecycleError):s.gate.issue(subject,'Bearer new',entitlement_reference='',scopes=(),
        valid_from=s.service.clock(),expires_at=s.service.clock()+timedelta(hours=1))
    with pytest.raises(LifecycleError) as denied:s.gate.authorize(replace(s.actors['a'],session_id='forged'))
    assert denied.value.status==401


@pytest.mark.parametrize('change',['expired','scope','revision'])
def test_session_authority_changes_deny_historical_retries(system,change):
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor=s.actors['a'];p=s.service.create(actor,request(),idempotency_key='cached')
    with s.unit.account(actor.subject) as conn:
        statement={'expired':'expires_at=:now','scope':"scopes='[]'::jsonb",'revision':'revision=revision+1'}[change]
        conn.execute(text('UPDATE customized_candidate_sessions SET '+statement+' WHERE subject=:s'),dict(s=actor.subject,now=s.service.clock()))
    with pytest.raises(LifecycleError) as denied:s.service.create(actor,request(),idempotency_key='cached')
    assert denied.value.status==(403 if change=='scope' else 401)


def test_missing_tail_revision_cannot_resurrect_withdrawn_consent(system):
    from types import SimpleNamespace
    from app.customized_postgres import _Transaction
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    a=s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    s.service.transition(actor,p['proposal_id'],'withdraw',expected_revision=a['revision'],idempotency_key='withdraw')
    with s.store.authorized_transaction(actor) as tx:
        class MissingTail:
            def execute(self,statement,*args,**kwargs):
                result=tx.connection.execute(statement,*args,**kwargs)
                if str(statement).startswith('SELECT revision,document,previous_digest,digest'):
                    rows=list(result.mappings())
                    return SimpleNamespace(mappings=lambda:rows[:-1])
                return result
        with pytest.raises(LifecycleError,match='candidate_replay_integrity'):
            _Transaction(MissingTail(),actor.subject).read(actor.subject,p['proposal_id'])


def test_sql_revision_keeps_previous_consent_historical_and_requires_new_ack(system):
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    accepted=s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    revised=s.service.revise(actor,p['proposal_id'],{**request(),'bundle_id':'longer-current','cap_minutes':90},
        expected_revision=accepted['revision'],idempotency_key='revise')
    assert revised['plan_version']==2 and revised['consent_receipt'] is None
    history=s.service.history(actor,p['proposal_id'])
    old=next(r for r in history if r['revision']==accepted['revision'])
    assert old['consent_receipt']==accepted['consent_receipt']
    with pytest.raises(LifecycleError):s.service.accept(actor,p['proposal_id'],data,idempotency_key='stale-version')
    c2=s.service.challenge(actor,p['proposal_id'],expected_revision=revised['revision'],snapshot_hash=revised['snapshot_hash'],
        idempotency_key='prepare2',protocol='compact-candidate-consent-v2')
    assert c2['summary_hash']!=c['summary_hash']
    assert len(c2['summary']['workload_changes'])==12
    assert len(c2['summary']['alternative_range_conflicts'])==6
    assert len(old['consent_receipt']['acknowledgements'])==20


def test_historical_retry_and_revocation_are_serialized(system):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    from threading import Event
    from app.customized_lifecycle_models import LifecycleError
    s=system;actor,p,c,data=prepared(s)
    accepted=s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    entered=Event();release=Event();original=s.store.authorized_transaction
    @contextmanager
    def paused(actor):
        with original(actor) as tx:
            entered.set();assert release.wait(4);yield tx
    s.store.authorized_transaction=paused
    with ThreadPoolExecutor(max_workers=2) as pool:
        retry=pool.submit(s.service.accept,actor,p['proposal_id'],data,idempotency_key='accept')
        assert entered.wait(4)
        revoke=pool.submit(s.change,'revoke',actor.subject)
        assert s.wait_for_lock(actor.subject);assert not revoke.done();release.set()
        assert retry.result(timeout=5)==accepted;revoke.result(timeout=5)
    s.store.authorized_transaction=original
    with pytest.raises(LifecycleError) as denied:s.service.accept(actor,p['proposal_id'],data,idempotency_key='accept')
    assert denied.value.status==401
