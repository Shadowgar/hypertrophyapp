"""Fresh-interpreter JWT/ownership probe; no production startup or DB connections.

Only invoked by the isolated test wrapper. In-memory transaction state proves the
identity bridge without allowing an ORM, SQLite or network connection. Existing
lifecycle persistence/concurrency tests separately qualify the disposable store.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def run():
    assert 'app.main' not in sys.modules and 'app.database' not in sys.modules
    class NoProductionMain(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname=='app.main':raise AssertionError('Production startup import attempted')
    sys.meta_path.insert(0,NoProductionMain())
    def deny_io(event,args):
        if event.startswith('sqlite3.') or event=='socket.connect':
            raise AssertionError('Database/network connection attempted')
        if event=='open':
            _,mode,flags=args
            if (mode and any(c in mode for c in 'wax+')) or flags & 3:
                raise AssertionError('Filesystem write attempted')
    sys.addaudithook(deny_io)

    from fastapi.testclient import TestClient
    from app.customized_lifecycle_http import create_lifecycle_app, existing_account_dependency
    assert 'app.database' not in sys.modules
    from app.customized_lifecycle import LifecycleService
    from research.m4c3a.fixtures import demo_server,demo_context
    from research.m4c3b1.demo import proposed_request,SyntheticSchedule
    from app.deps import get_db
    from app.models import User
    from app.security import create_access_token

    class MemoryStore:
        def __init__(self): self.documents={};self.retries={}
        @contextmanager
        def transaction(self):
            before=deepcopy((self.documents,self.retries))
            try:yield self
            except BaseException:
                self.documents,self.retries=before
                raise
        def read(self,subject,id):return deepcopy(self.documents.get((subject,id)))
        def append(self,subject,document,expected_revision):
            old=self.read(subject,document['proposal_id'])
            assert (old['revision'] if old else 0)==expected_revision
            self.documents[subject,document['proposal_id']]=deepcopy(document)
        def retry(self,subject,key):return deepcopy(self.retries.get((subject,key)))
        def remember(self,subject,key,digest,response):self.retries[subject,key]=(digest,deepcopy(response))
    class Lookup:
        def filter(self,predicate):self.subject=predicate.right.value;return self
        def first(self):return User(id=self.subject) if self.subject in {'alice','bob'} else None
    def disposable_lookup():yield SimpleNamespace(query=lambda model:Lookup())
    service=LifecycleService(server=replace(demo_server(),allowed_subjects=('alice','bob')),store=MemoryStore(),
        schedule=SyntheticSchedule(),clock=lambda:demo_context().planning_instant,
        comparison_pairs=(('shorter-current','longer-current'),))
    app=create_lifecycle_app(service=service,account_dependency=existing_account_dependency(),trusted_origin='http://testserver')
    app.dependency_overrides[get_db]=disposable_lookup
    client=TestClient(app)
    alice=create_access_token('alice');bob=create_access_token('bob')
    p=client.post('/customized/proposals',json=proposed_request(),headers={
        'Authorization':'Bearer '+alice,'Origin':'http://testserver','Idempotency-Key':'probe-create'}).json()
    assert p['subject']=='alice'
    for id in (p['proposal_id'],'unknown'):
        r=client.get('/customized/proposals/'+id,headers={'Authorization':'Bearer '+bob})
        assert r.status_code==404 and r.json()=={'status':'not_found'}
    for token in ('forged.invalid.token',create_access_token('absent')):
        assert client.get('/customized/proposals/unknown',headers={'Authorization':'Bearer '+token}).status_code==401
    assert 'app.main' not in sys.modules
    # A positive control establishes that the connection guard is actually live.
    import sqlite3
    try:sqlite3.connect(':memory:')
    except AssertionError:pass
    else:raise AssertionError('Connection guard inactive')
    import os
    from sqlalchemy.engine import make_url
    assert not Path(make_url(os.environ['DATABASE_URL']).database).exists()
    print(json.dumps(dict(authenticated_owner=True,cross_account_http=404,invalid_or_absent_user_http=401,
        production_main_imported=False,database_connections=0,connection_guard_verified=True)))


if __name__=='__main__':run()
